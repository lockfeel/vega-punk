import asyncio
import threading
from datetime import datetime
from typing import Optional



class Session:

    def __init__(self, userId: str, sessionKey: str, botId: str = 'vega-punk'):
        self.userId = userId
        self.sessionKey = sessionKey
        self.botId = botId
        self.createdAt = datetime.now()
        self.lastActive = datetime.now()

    def touch(self):
        self.lastActive = datetime.now()


class SessionManager:

    def __init__(self, gateway, db, idleTimeout: int = 86400):
        self.gateway = gateway
        self.db = db
        self.idleTimeout = idleTimeout
        self._lock = threading.RLock()
        self._gcTask: Optional[asyncio.Task] = None

    async def start(self):
        self._gcTask = asyncio.create_task(self._garbageCollector())

    async def stop(self):
        if self._gcTask: self._gcTask.cancel()

    async def getOrCreate(self, userId: str, botId: str = 'vega-punk') -> Optional[Session]:
        if not userId: return None
        with self._lock:
            dbRow = self.db.getSession(userId, botId)
            if dbRow:
                return Session(
                    userId=dbRow['userId'],
                    sessionKey=dbRow['sessionKey'],
                    botId=dbRow['botId']
                )
            if botId == 'openclaw':
                dbRow = self.db.getOpenclawSession()
                if dbRow:
                    return Session(
                        userId=dbRow['userId'],
                        sessionKey=dbRow['sessionKey'],
                        botId=dbRow['botId']
                    )
                self.db.createSession(userId='openclaw', botId='openclaw', sessionKey='agent:main:main')
                return Session(userId='openclaw', sessionKey='agent:main:main', botId='openclaw')
            else:
                sessionKey = f"agent:main:user-{userId}-{botId}"
            try:
                await self.gateway.sendRequest("sessions.create", {"key": sessionKey})
            except Exception as e:
                pass

            self.db.createSession(userId=userId, botId=botId, sessionKey=sessionKey)
            return Session(userId, sessionKey, botId)

    def activeBySession(self, sessionKey: str):
        self.db.touchSessionByKey(sessionKey)

    def getBySessionKey(self, sessionKey: str) -> Optional[Session]:
        with self._lock:
            dbRow = self.db.getSessionByKey(sessionKey)
            if dbRow:
                self.db.touchSessionByKey(sessionKey)
                return Session(
                    userId=dbRow['userId'],
                    sessionKey=dbRow['sessionKey'],
                    botId=dbRow['botId']
                )
            dbRow = self.db.getOpenclawSession()
            if dbRow:
                if dbRow['sessionKey'] != sessionKey:
                    self.db.updateSessionKey(userId='openclaw', botId='openclaw', sessionKey=sessionKey)
                return Session(
                    userId=dbRow['userId'],
                    sessionKey=sessionKey,
                    botId=dbRow['botId']
                )
            self.db.createSession(userId='openclaw', botId='openclaw', sessionKey=sessionKey)
            return Session(userId='openclaw', sessionKey=sessionKey, botId='openclaw')

    async def close(self, userId: str, botId: str = 'vega-punk'):
        with (self._lock):
            dbRow = self.db.getSession(userId, botId)
            if dbRow:
                try:
                    await self.gateway.deleteSession(dbRow['sessionKey'])
                    self.db.closeSessionByKey(dbRow['sessionKey'])
                except Exception as e:
                    pass

    async def _garbageCollector(self):
        while True:
            try:
                await asyncio.sleep(600)
                idleSessions = self.db.getIdleSessions(self.idleTimeout)
                for row in idleSessions:
                    await self.close(row['userId'], row['botId'])
            except asyncio.CancelledError:
                break
            except Exception as e:
                pass