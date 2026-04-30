# -*- coding: utf-8 -*-
import asyncio
import json
import os
import sys
import uuid

import uvicorn

rootDir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(f"{os.path.dirname(rootDir)}")
sys.path.append(f"{rootDir}")

from contextlib import asynccontextmanager
from service.gateway.chat_handler import ChatHandler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from starlette.websockets import WebSocket, WebSocketDisconnect
from utils.common_util import clearPycache
from utils.token_util import verifyToken
from utils.db_util import DBase
from gateway import (
    OpenClawGatewayClient,
    SessionManager,
    getOpenclawConfig,
)

gatewayClient: OpenClawGatewayClient | None = None
sessionManager: SessionManager | None = None
db: DBase | None = None

# OpenClaw 内置命令（这些命令不做加工，直接透传）
OPENCLAW_BUILTIN_COMMANDS = {
    '/help',
    '/commands',
    '/tools',
    '/status',
    '/tasks',
    '/whoami',
    '/usage',
    '/models',
    '/session',
    '/reset',
    '/new',
    '/compact',
    '/stop',
    '/restart',
    '/clear',
    '/skill',
    '/tts',
    '/context',
    '/btw',
    '/reasoning',
    '/think',
    '/verbose',
    '/fast',
    '/model',
    '/queue',
    '/subagents',
    '/agents',
    '/kill',
    '/steer',
    '/acp',
    '/focus',
    '/unfocus',
    '/config',
    '/mcp',
    '/debug',
    '/allowlist',
    '/approve',
    '/activation',
    '/send',
    '/elevated',
    '/exec',
    '/bash',
    '/webhook',
}


@asynccontextmanager
async def lifespan(app):
    global gatewayClient, sessionManager, db
    db = DBase()
    cfg = getOpenclawConfig()

    if cfg.get("enabled"):
        gatewayClient = OpenClawGatewayClient(url=cfg["url"], token=cfg["token"])
        try:
            await asyncio.wait_for(gatewayClient.connect(), timeout=30)
            sessionManager = SessionManager(gatewayClient, db)
            await sessionManager.start()
        except Exception as e:
            pass
    elif cfg.get("error"):
        pass
    else:
        pass

    yield

    if sessionManager:
        await sessionManager.stop()
    if gatewayClient:
        await gatewayClient.close()


app = FastAPI(lifespan=lifespan)


def _render(path: str) -> str:
    with open(f"{rootDir}/templates/{path}", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
async def root():
    return _render("login.html")


@app.get("/chats", response_class=HTMLResponse)
async def chatsPage(request: Request):
    queryToken = request.query_params.get("token")
    cookieToken = request.cookies.get("userToken")
    token = queryToken or cookieToken
    if not token or not verifyToken(token):
        return RedirectResponse(url="/login", status_code=302)
    response = HTMLResponse(_render("chats.html"))
    if queryToken:
        response.set_cookie(key="userToken", value=queryToken, httponly=True, samesite="lax")
    return response


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.post("/bots")
async def listBots():
    if not db:
        return JSONResponse({"error": "数据库未就绪"}, status_code=503)
    bots = db.getAllBots()
    return JSONResponse({"bots": bots})


@app.post("/active")
async def activeChats():
    if not db:
        return JSONResponse({"error": "数据库未就绪"}, status_code=503)
    result = db.getActiveChats()
    return JSONResponse({"active": result})


@app.post("/messages")
async def getMessages(request: Request):
    if not db:
        return JSONResponse({"error": "数据库未就绪"}, status_code=503)
    body = await request.json()
    botId = body.get("botId", "vega-punk")
    limit = body.get("limit", 200)
    result = db.getBotMessages(botId, limit)
    return JSONResponse({"messages": result})


@app.post("/delete-chat")
async def deleteChat(request: Request):
    if not db or not sessionManager:
        return JSONResponse({"error": "服务未就绪"}, status_code=503)
    body = await request.json()
    botId = body.get("botId")
    if not botId: return JSONResponse({"error": "缺少 botId"}, status_code=400)
    db.clearMessagesByBotId(botId)
    sessions = db.getSessionsByBotId(botId)
    for row in sessions:
        await gatewayClient.sendRequest("sessions.delete", {"key": row['sessionKey']})
        db.closeSessionByKey(row['sessionKey'])
    return JSONResponse({"success": True, "botId": botId})


def _preprocessMessage(message: str, botId: str) -> str:
    """对非内置命令的消息进行 botId 前缀加工，已带前缀的不再重复添加"""
    if not message or botId == 'openclaw':
        return message
    if message == '/init-bot':
        return f'/{botId} 加载并激活这个SKILL，并根据这个SKILL的功能描述，给用户输出一段使用指南。'
    # 检查消息是否已经带有当前 botId 前缀
    prefix = f'/{botId}'
    if message.startswith(prefix) and (len(message) == len(prefix) or message[len(prefix)] in (' ', '\t')):
        return message
    return f'/{botId} {message}'


def _isBuiltinCommand(message: str) -> bool:
    if not message:
        return False
    cmd = message.split()[0].lower()
    return cmd in OPENCLAW_BUILTIN_COMMANDS


@app.websocket("/chatClaw")
async def chatClaw(websocket: WebSocket):
    await websocket.accept()
    if not gatewayClient or not sessionManager:
        await websocket.send_json({"error": "OpenClaw 未就绪"})
        await websocket.close()
        return
    handler = ChatHandler(websocket, sessionManager, gatewayClient, db)
    gatewayClient.onEvent("agent", handler.handle)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            userId = msg.get('user')
            message = msg.get('text')
            botId = msg.get('botId', 'vega-punk')

            # ping 心跳
            if msg.get('type') == 'ping':
                session = await sessionManager.getOrCreate(userId, botId)
                if session:
                    sessionManager.activeBySession(session.sessionKey)
                continue

            # 参数校验
            if not userId or not message:
                await websocket.send_json({"error": "缺少 user 或 message"})
                continue

            # 连接状态检查
            if not gatewayClient.connected.is_set():
                await websocket.send_json({"error": "OpenClaw未连接"})
                continue

            # 记录用户消息
            db.addMessage(botId=botId, senderId=userId, role='user', content=message)

            # 获取或创建 session
            session = await sessionManager.getOrCreate(userId, botId)
            if not session:
                await websocket.send_json({"error": "session 创建失败"})
                continue

            # 消息预处理并发送
            if not _isBuiltinCommand(message): message = _preprocessMessage(message, botId)
            await gatewayClient.sendChat(
                session.sessionKey,
                message,
                idempotencyKey=msg.get("idempotency_key", f"{userId}-{uuid.uuid4().hex[:8]}")
            )
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        gatewayClient.offEvent("agent", handler.handle)


if __name__ == '__main__':
    clearPycache()
    uvicorn.run(app, host="127.0.0.1", port=8893)
