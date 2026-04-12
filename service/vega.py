# -*- coding: utf-8 -*-
import asyncio
import json
import logging
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
    logger,
    getOpenclawConfig,
)

gatewayClient = None
sessionManager = None
db = None


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
            logging.info("[Vaga] OpenClaw 中间件已启动")
        except Exception as e:
            logging.error(f"[Vaga] 连接失败: {e}")
    elif cfg.get("error"):
        logging.warning(f"[Vaga] 配置加载失败: {cfg['error']}")
    else:
        logging.warning("[Vaga] 未配置 token，OpenClaw 功能将不可用")

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


@app.websocket("/chatClaw")
async def chatClaw(websocket: WebSocket):
    await websocket.accept()
    if not gatewayClient or not sessionManager:
        await websocket.send_json({"error": "OpenClaw 未就绪"})
        await websocket.close()
        return
    accumulatedText = ''

    async def onChatEvent(payload: dict):
        nonlocal accumulatedText
        print(payload)
        runId = payload.get('runId')
        stream = payload.get('stream')
        phase = payload.get('data', {}).get('phase')
        eventSession = payload.get('sessionKey', '')
        currSession = sessionManager.getBySessionKey(eventSession)
        botId = None
        if currSession:
            botId = currSession.botId
            sessionManager.activeBySession(eventSession)
        data = payload.get('data', {})
        if 'HEARTBEAT' in data.get('text', ''): return
        if phase == 'end' and data.get('text', '') == '':
            try:
                if accumulatedText.strip():
                    sessionKey = payload.get('sessionKey', '')
                    db.addMessage(botId=botId, senderId=sessionKey, role='assistant', content=accumulatedText)
                    accumulatedText = ''
                    return
            except Exception as e:
                logger.error(f"[WS] 发送 final 失败: {e}")
        if stream == 'assistant' and phase is None:
            accumulatedText = data.get('text', '')
            try:
                await websocket.send_json({
                    "type": "delta",
                    "runId": runId,
                    "sessionKey": payload.get('sessionKey'),
                    "botId": botId,
                    "text": accumulatedText,
                    "delta": data.get('delta', '')
                })
            except Exception as e:
                logger.error(f"[WS] 发送 delta 失败: {e}")
        if stream == 'item':
            toolName = data.get('name') or data.get('tool')
            phase = data.get('phase')
            if toolName == 'read' and phase == 'start':
                title = data.get('title', '')
                if 'SKILL.md' in title:
                    match = re.search(r'[~/\w.\-]+/skills/[^/]+/SKILL\.md', title)
                    filePath = match.group(0) if match else ''
                    skillName = getSkillName(filePath)
                    await websocket.send_json({
                        "type": "delta",
                        "runId": runId,
                        "sessionKey": payload.get('sessionKey'),
                        "botId": skillName,
                        "text": f"{skillName}正在为您工作",
                        "delta": ""
                    })

    gatewayClient.onEvent("agent", onChatEvent)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            userId = msg.get('user')
            message = msg.get('text')
            botId = msg.get('botId', 'vega-punk')
            session = await sessionManager.getOrCreate(userId, botId)
            if msg.get('type') == 'ping':
                if session: sessionManager.activeBySession(session.sessionKey)
                continue
            if not userId or not message:
                await websocket.send_json({"error": "缺少 user 或 message"})
                continue
            if not gatewayClient.connected.is_set():
                await websocket.send_json({"error": "OpenClaw未连接"})
                continue
            db.addMessage(botId=botId, senderId=userId, role='user', content=message)
            try:
                if message == '/init-bot' and botId != 'openclaw':
                    message = f'/{botId} 加载并激活这个SKILL，并根据这个SKILL的功能描述，给用户输出一段使用指南。'
                else:
                    if botId != 'openclaw':
                        message = f'/{botId} {message}'
                await gatewayClient.sendChat(
                    session.sessionKey,
                    message,
                    idempotencyKey=msg.get("idempotency_key", f"{userId}-{uuid.uuid4().hex[:8]}")
                )
            except Exception as e:
                logger.error(f"[WS] 发送消息失败: {e}")
                await websocket.send_json({"type": "error", "error": str(e)})
    except WebSocketDisconnect:
        logger.info("[WS] 客户端断开")
    except Exception as e:
        logger.error(f"[WS] 错误: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        gatewayClient.offEvent("agent", onChatEvent)


if __name__ == '__main__':
    clearPycache()
    uvicorn.run(app, host="127.0.0.1", port=8893)
