# -*- coding: utf-8 -*-
import asyncio
import json
import os
import re
import sys
import uuid

import uvicorn

from service.utils.common_util import getSkillName

rootDir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(f"{os.path.dirname(rootDir)}")
sys.path.append(f"{rootDir}")

from contextlib import asynccontextmanager
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

gatewayClient = None
sessionManager = None
db = None

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
    if not botId:
        return JSONResponse({"error": "缺少 botId"}, status_code=400)
    db.clearMessagesByBotId(botId)
    sessions = db.getSessionsByBotId(botId)
    for row in sessions:
        try:
            await gatewayClient.sendRequest("sessions.delete", {"key": row['sessionKey']})
        except Exception:
            pass
        db.closeSessionByKey(row['sessionKey'])
    return JSONResponse({"success": True, "botId": botId})


def _preprocessMessage(message: str, botId: str) -> str:
    """对非内置命令的消息进行 botId 前缀加工"""
    if not message or botId == 'openclaw':
        return message
    if message == '/init-bot':
        return f'/{botId} 加载并激活这个SKILL，并根据这个SKILL的功能描述，给用户输出一段使用指南。'
    return f'/{botId} {message}'


def _isBuiltinCommand(message: str) -> bool:
    if not message:
        return False
    cmd = message.split()[0].lower()
    return cmd in OPENCLAW_BUILTIN_COMMANDS


class ChatHandler:

    def __init__(self, websocket: WebSocket):
        self.currSession = None
        self.sessionKey = None
        self.websocket = websocket
        self.accumulatedText = ''
        self.handoffCache: set = set()

    async def handle(self, payload: dict):
        stream = payload.get('stream')
        data = payload.get('data', {})

        if 'HEARTBEAT' in data.get('text', ''):
            return

        self.sessionKey = payload.get('sessionKey', '')
        self.currSession = sessionManager.getBySessionKey(self.sessionKey) if sessionManager else None
        if self.currSession:
            sessionManager.activeBySession(self.sessionKey)

        if stream == 'assistant':
            await self._handleAssistant(payload, data)
        elif stream == 'item':
            await self._handleItem(payload, data)

    async def _handleAssistant(self, payload: dict, data: dict):
        phase = data.get('phase')
        # phase=None 表示流式输出
        if phase is None:
            self.accumulatedText = data.get('text', '')
            await self._sendJson({
                "type": "delta",
                "runId": payload.get('runId'),
                "sessionKey": self.sessionKey,
                "botId": self.currSession.botId if self.currSession else None,
                "text": self.accumulatedText,
                "delta": data.get('delta', '')
            })
            return
        # phase=end 表示输出结束
        if phase == 'end' and not data.get('text', '') and self.accumulatedText.strip():
            db.addMessage(
                botId=self.currSession.botId if self.currSession else None,
                senderId=self.sessionKey,
                role='assistant',
                content=self.accumulatedText
            )
            self.accumulatedText = ''

    async def _handleItem(self, payload: dict, data: dict):
        toolName = data.get('name') or data.get('tool')
        phase = data.get('phase')
        if toolName != 'read' or phase != 'start':
            return

        title = data.get('title', '')
        if 'SKILL.md' not in title:
            return

        match = re.search(r'[~/\w.\-]+/skills/[^/]+/SKILL\.md', title)
        filePath = match.group(0) if match else ''
        skillName = getSkillName(filePath)
        if not skillName or skillName in self.handoffCache:
            return

        self.handoffCache.add(skillName)
        await self._doHandoff(payload, skillName)

    async def _doHandoff(self, payload: dict, skillName: str):
        if not self.currSession:
            return

        skillSession = await sessionManager.getOrCreate(self.currSession.userId, skillName)
        if not skillSession:
            return

        await self._sendJson({
            "type": "handoff",
            "runId": payload.get('runId'),
            "sessionKey": skillSession.sessionKey,
            "botId": skillName,
            "text": f"{skillName}正在为您工作",
            "fromBotId": self.currSession.botId
        })

        lastUserMsg = db.getLastUserMessage(self.currSession.userId, self.currSession.botId)
        handoffMsg = f"请接管处理以下请求：\n\n{lastUserMsg}" if lastUserMsg else "请根据 SKILL 描述开始工作"
        await gatewayClient.sendChat(
            skillSession.sessionKey,
            handoffMsg,
            idempotencyKey=f"handoff-{skillName}-{payload.get('runId')}"
        )

    async def _sendJson(self, data: dict):
        try:
            await self.websocket.send_json(data)
        except Exception:
            pass


@app.websocket("/chatClaw")
async def chatClaw(websocket: WebSocket):
    await websocket.accept()
    if not gatewayClient or not sessionManager:
        await websocket.send_json({"error": "OpenClaw 未就绪"})
        await websocket.close()
        return

    handler = ChatHandler(websocket)
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
            try:
                if not _isBuiltinCommand(message):
                    message = _preprocessMessage(message, botId)
                await gatewayClient.sendChat(
                    session.sessionKey,
                    message,
                    idempotencyKey=msg.get("idempotency_key", f"{userId}-{uuid.uuid4().hex[:8]}")
                )
            except Exception as e:
                await websocket.send_json({"type": "error", "error": str(e)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        gatewayClient.offEvent("agent", handler.handle)


if __name__ == '__main__':
    clearPycache()
    uvicorn.run(app, host="127.0.0.1", port=8893)
