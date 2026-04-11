# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import sys
import uuid

import uvicorn

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
    OutputFilter,
    SecurityAudit,
    RiskLevel,
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
            sessionManager = SessionManager(gatewayClient, idleTimeout=1800)
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
    currentSessionKey = None
    accumulatedText = ""
    savedRunIds = set()

    async def onChatEvent(payload: dict):
        nonlocal currentSessionKey, accumulatedText
        runId = payload.get('runId')
        stream = payload.get('stream')
        phase = payload.get('data', {}).get('phase')
        eventSession = payload.get('sessionKey', '')

        botId = None
        try:
            session = sessionManager.getBySessionKey(eventSession)
            if session:
                botId = session.botId
                sessionManager.activeBySession(eventSession)
        except Exception:
            pass

        if stream == 'assistant':
            try:
                data = payload.get('data', {})
                accumulatedText = data.get('text', '')
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

        elif phase == 'end':
            if runId and runId in savedRunIds:
                return
            if runId:
                savedRunIds.add(runId)
            try:
                hasDangerous, dangerousCmds = OutputFilter.auditOutput(accumulatedText)
                responseData = {
                    "type": "final",
                    "runId": runId,
                    "sessionKey": payload.get('sessionKey'),
                    "botId": botId,
                    "content": accumulatedText,
                    "state": "completed"
                }
                if hasDangerous:
                    responseData["security_warning"] = {
                        "detected": True,
                        "commands": dangerousCmds[:3],
                        "message": "⚠️ 检测到潜在危险命令，请确认安全后再执行"
                    }
                    logger.warning(f"[Security] AI 输出包含危险命令: {dangerousCmds}")
                await websocket.send_json(responseData)

                if accumulatedText.strip() and accumulatedText.strip() != "HEARTBEAT_OK":
                    sessionKey = payload.get('sessionKey', '')
                    db.addMessage(botId=botId, senderId=sessionKey, role='assistant', content=accumulatedText)
            except Exception as e:
                logger.error(f"[WS] 发送 final 失败: {e}")

    gatewayClient.onEvent("agent", onChatEvent)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get('type') == 'ping':
                if currentSessionKey:
                    try:
                        sessionManager.activeBySession(currentSessionKey)
                    except Exception:
                        pass
                continue

            userId = msg.get('user')
            message = msg.get('text')
            botId = msg.get('botId', 'vega-punk')
            if not userId or not message:
                await websocket.send_json({"error": "缺少 user 或 message"})
                continue
            if not gatewayClient.connected.is_set():
                await websocket.send_json({"error": "OpenClaw未连接"})
                continue

            session = await sessionManager.getOrCreate(userId, botId)
            db.addMessage(botId=botId, senderId=userId, role='user', content=message)
            riskLevel, riskReason = SecurityAudit.audit(message)
            logger.info(f"[Security] user={userId}, risk={riskLevel.value}, reason={riskReason}")
            if riskLevel == RiskLevel.CRITICAL:
                await websocket.send_json({
                    "type": "error",
                    "error": f"🚫 指令被阻止: {riskReason}",
                    "risk": "critical"
                })
                continue
            if riskLevel == RiskLevel.HIGH:
                await websocket.send_json({
                    "type": "error",
                    "error": f"⚠️ 高风险指令: {riskReason}",
                    "risk": "high"
                })
                continue

            try:
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
