# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Dict, Optional

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)

RECONNECT_DELAYS = [1, 2, 5, 10, 30, 60]
MAX_RECONNECT_ATTEMPTS = 10


class OpenClawGatewayClient:

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token

        self.ws: Optional[WebSocketClientProtocol] = None
        self._isConnecting = False
        self._isAborted = False

        self._connected = asyncio.Event()
        self._pending: Dict[str, asyncio.Future] = {}
        self._eventHandlers: Dict[str, Callable] = {}

        self._reconnectAttempts = 0
        self._reconnectTimer: Optional[asyncio.TimerHandle] = None

        self._heartbeatInterval: Optional[asyncio.Task] = None

        self._lock = asyncio.Lock()

    async def connect(self):
        self._isAborted = False

        while not self._isAborted:
            try:
                await self._doConnect()
                self._reconnectAttempts = 0
                self._connected.set()
                logger.info("[OpenClaw] 连接成功")
                return
            except Exception as e:
                logger.error(f"[OpenClaw] 连接失败: {e}")
                await self._scheduleReconnect()

    async def _doConnect(self):
        if self._isConnecting:
            logger.debug("[OpenClaw] 已在连接中")
            await asyncio.sleep(1)
            if self._connected.is_set():
                return
            raise Exception("连接中")

        self._isConnecting = True
        try:
            await self._cleanup()

            logger.info(f"[OpenClaw] 连接网关: {self.url}")
            self.ws = await websockets.connect(
                self.url,
                ping_interval=None,
                origin="http://127.0.0.1:18789"
            )
            logger.info("[OpenClaw] WebSocket 连接已建立")

            asyncio.create_task(self._messageHandler())

            logger.info("[OpenClaw] 等待 challenge...")
            challenge = await self._waitForEvent("connect.challenge", timeout=10)
            if not challenge:
                raise Exception("未收到 connect.challenge")

            nonce = challenge["payload"]["nonce"]
            logger.info(f"[OpenClaw] 收到 challenge")

            connectId = str(uuid.uuid4())
            future = self._pending[connectId] = asyncio.Future()

            connectMsg = {
                "type": "req",
                "id": connectId,
                "method": "connect",
                "params": {
                    "minProtocol": 3,
                    "maxProtocol": 5,
                    "client": {
                        "id": "openclaw-control-ui",
                        "version": "V1.0.1",
                        "platform": "python",
                        "mode": "webchat"
                    },
                    "role": "operator",
                    "scopes": [
                        "operator.admin",
                        "operator.read",
                        "operator.write",
                        "operator.approvals",
                        "operator.pairing"
                    ],
                    "auth": {"token": self.token}
                }
            }
            await self.ws.send(json.dumps(connectMsg))
            await asyncio.wait_for(future, timeout=15)
            self._startHeartbeat()

        finally:
            self._isConnecting = False

    async def _cleanup(self):
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None

        if self._heartbeatInterval:
            self._heartbeatInterval.cancel()
            self._heartbeatInterval = None

        for future in self._pending.values():
            if not future.done(): future.set_exception(Exception("连接已关闭"))
        self._pending.clear()
        self._connected.clear()

    def _getReconnectDelay(self) -> float:
        idx = min(self._reconnectAttempts, len(RECONNECT_DELAYS) - 1)
        return RECONNECT_DELAYS[idx]

    async def _scheduleReconnect(self):
        if self._isAborted:
            return

        if self._reconnectTimer:
            self._reconnectTimer.cancel()

        if self._reconnectAttempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error("[OpenClaw] 达到最大重连次数")
            return

        delay = self._getReconnectDelay()
        self._reconnectAttempts += 1

        logger.info(f"[OpenClaw] {delay}s 后重连 (尝试 {self._reconnectAttempts}/{MAX_RECONNECT_ATTEMPTS})")

        async def doReconnect():
            if not self._isAborted:
                await self.connect()

        self._reconnectTimer = asyncio.get_event_loop().call_later(delay, lambda: asyncio.create_task(doReconnect()))

    def abort(self):
        self._isAborted = True
        if self._reconnectTimer:
            self._reconnectTimer.cancel()
            self._reconnectTimer = None

    def _startHeartbeat(self):
        if self._heartbeatInterval:
            self._heartbeatInterval.cancel()

        async def heartbeat():
            while self._connected.is_set() and self.ws:
                try:
                    if self.ws.state == websockets.protocol.State.OPEN:
                        await self.ws.send(json.dumps({"type": "ping"}))
                        logger.debug("[OpenClaw] 心跳已发送")
                    await asyncio.sleep(30)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"[OpenClaw] 心跳异常: {e}")
                    break

        self._heartbeatInterval = asyncio.create_task(heartbeat())

    async def _messageHandler(self):
        try:
            async for message in self.ws:
                try:
                    msg = json.loads(message)
                    msgType = msg.get("type")

                    if msgType == "res":
                        pending = self._pending.pop(msg.get("id"), None)
                        if pending:
                            if msg.get("ok"):
                                pending.set_result(msg.get("payload", {}))
                            else:
                                error = msg.get("error", {})
                                pending.set_exception(Exception(error.get("message", "网关错误")))

                    elif msgType == "event":
                        event = msg.get("event")
                        payload = msg.get("payload", {})

                        handler = self._eventHandlers.get(event)
                        if handler:
                            handlers = [handler] if not isinstance(handler, list) else handler
                            for h in handlers:
                                try:
                                    if asyncio.iscoroutinefunction(h):
                                        await h(payload)
                                    else:
                                        h(payload)
                                except Exception as e:
                                    logger.error(f"[OpenClaw] 事件处理错误: {e}")

                        any_handlers = self._eventHandlers.get("any", [])
                        if any_handlers:
                            any_handlers = [any_handlers] if not isinstance(any_handlers, list) else any_handlers
                            for h in any_handlers:
                                try:
                                    if asyncio.iscoroutinefunction(h):
                                        await h(event, payload)
                                    else:
                                        h(event, payload)
                                except Exception as e:
                                    logger.error(f"[OpenClaw] any 事件处理错误: {e}")

                    elif msgType == "ping":
                        logger.debug("[OpenClaw] 收到 ping")

                    else:
                        logger.debug(f"[OpenClaw] 未知消息: {msgType}")

                except json.JSONDecodeError:
                    logger.warning("[OpenClaw] 无效 JSON")
                except Exception as e:
                    logger.error(f"[OpenClaw] 消息处理错误: {e}")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"[OpenClaw] 连接关闭: {e}")
            self._connected.clear()
            if not self._isAborted:
                await self._scheduleReconnect()

    async def _waitForEvent(self, eventName: str, timeout: float = 30):
        future = asyncio.Future()

        def handler(payload):
            if not future.done():
                future.set_result({"event": eventName, "payload": payload})

        self.onEvent(eventName, handler, once=True)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self.offEvent(eventName, handler)

    async def sendRequest(self, method: str, params: dict, timeout: float = 60) -> Any:
        if not self._connected.is_set():
            await self.connect()

        requestId = str(uuid.uuid4())
        future = self._pending[requestId] = asyncio.Future()

        msg = {
            "type": "req",
            "id": requestId,
            "method": method,
            "params": params
        }

        try:
            await self.ws.send(json.dumps(msg))
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(requestId, None)
            raise Exception(f"请求超时: {method}")

    async def sendChat(self, sessionKey: str, message: str, idempotencyKey: Optional[str] = None):
        params = {
            "sessionKey": sessionKey,
            "message": message,
            "idempotencyKey": idempotencyKey or str(uuid.uuid4())
        }
        return await self.sendRequest("chat.send", params)

    def onEvent(self, eventName: str, handler: Callable, once: bool = False):
        if once:
            original = handler

            def wrapper(payload):
                self.offEvent(eventName, wrapper)
                original(payload)

            handler = wrapper

        if eventName not in self._eventHandlers:
            self._eventHandlers[eventName] = []
        self._eventHandlers[eventName].append(handler)

    def offEvent(self, eventName: str, handler: Callable = None):
        if eventName not in self._eventHandlers:
            return
        if handler is None:
            self._eventHandlers.pop(eventName, None)
        else:
            self._eventHandlers[eventName] = [h for h in self._eventHandlers[eventName] if h != handler]

    async def close(self):
        self.abort()
        await self._cleanup()
        logger.info("[OpenClaw] 连接已关闭")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def connected(self):
        return self._connected
