import asyncio
import logging
import threading
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class Session:

    def __init__(self, userId: str, sessionKey: str):
        self.userId = userId
        self.sessionKey = sessionKey
        self.createdAt = datetime.now()
        self.lastActive = datetime.now()

    def touch(self):
        self.lastActive = datetime.now()

    def isIdle(self, timeoutSeconds: int) -> bool:
        return (datetime.now() - self.lastActive).total_seconds() > timeoutSeconds


class SessionManager:

    def __init__(self, gateway, idleTimeout: int = 1800):
        self.gateway = gateway
        self.idleTimeout = idleTimeout
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()
        self._gcTask: Optional[asyncio.Task] = None

    async def start(self):
        self._gcTask = asyncio.create_task(self._garbageCollector())
        logger.info("[Session] 管理器启动")

    async def stop(self):
        if self._gcTask: self._gcTask.cancel()

    async def getOrCreate(self, userId: str) -> Session:
        with self._lock:
            session = self._sessions.get(userId)

            if session is None:
                sessionKey = f"agent:main:user-{userId}"
                try:
                    await self.gateway.sendRequest("sessions.create", {
                        "key": sessionKey
                    })
                except Exception as e:
                    logger.warning(f"[Session] 创建失败: {e}")

                session = Session(userId, sessionKey)
                self._sessions[userId] = session

            session.touch()
            return session

    def active(self, userId: str):
        with self._lock:
            session = self._sessions.get(userId)
            if session:
                session.touch()

    def activeBySession(self, sessionKey: str):
        with self._lock:
            for session in self._sessions.values():
                if session.sessionKey == sessionKey:
                    session.touch()
                    break

    async def get(self, userId: str) -> Optional[Session]:
        with self._lock:
            session = self._sessions.get(userId)
            if session: session.touch()
            return session

    async def close(self, userId: str):
        with self._lock:
            session = self._sessions.pop(userId, None)
            if session:
                try:
                    await self.gateway.sendRequest("sessions.delete", {"key": session.sessionKey})
                    logger.info(f"[Session] 关闭: {userId}")
                except Exception as e:
                    logger.error(f"[Session] 关闭失败 {userId}: {e}")

    async def _garbageCollector(self):
        while True:
            try:
                await asyncio.sleep(600)
                idleSessions = []
                with self._lock:
                    for userId, session in list(self._sessions.items()):
                        if session.isIdle(self.idleTimeout): idleSessions.append((userId, session))

                for userId, session in idleSessions:
                    logger.info(f"[Session] GC: 清理闲置会话 {userId}")
                    await self.close(userId)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Session] GC 错误: {e}")
