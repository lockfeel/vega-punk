# -*- coding: utf-8 -*-
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional


def _rowToDict(row) -> Dict[str, Any]:
    if row is None:
        return {}
    return dict(row)


def _rowsToDicts(rows) -> List[Dict[str, Any]]:
    return [_rowToDict(r) for r in rows]


class DBase:
    def __init__(self, dbPath: str = None):
        if dbPath is None:
            dbPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.db")
        self.dbPath = dbPath
        os.makedirs(os.path.dirname(dbPath), exist_ok=True)
        self._initDb()

    def _initDb(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS bots (
                    botId TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'pm',
                    avatar TEXT,
                    managerId TEXT,
                    status TEXT DEFAULT 'idle',
                    progress INTEGER DEFAULT 0,
                    createTime INTEGER DEFAULT (strftime('%s', 'now')),
                    lastTime INTEGER DEFAULT (strftime('%s', 'now')),
                    deleted INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    botId TEXT,
                    senderId TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    createTime INTEGER DEFAULT (strftime('%s', 'now')),
                    deleted INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(senderId, createTime);
                CREATE INDEX IF NOT EXISTS idx_messages_bot ON messages(botId, createTime);
                CREATE TABLE IF NOT EXISTS sessions (
                    userId TEXT NOT NULL,
                    botId TEXT NOT NULL,
                    sessionKey TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    createTime INTEGER DEFAULT (strftime('%s', 'now')),
                    lastActive INTEGER DEFAULT (strftime('%s', 'now')),
                    deleted INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_user_bot ON sessions(userId, botId, status);
                CREATE INDEX IF NOT EXISTS idx_sessions_key ON sessions(sessionKey, status, deleted);
                CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(status, lastActive);
            """)

        self._migrateSessions()
        self._initBots()

    def _migrateSessions(self):
        """如果 sessions 表缺少 botId 列，则自动迁移"""
        try:
            with self._conn() as conn:
                cursor = conn.execute("PRAGMA table_info(sessions)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'botId' not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN botId TEXT DEFAULT 'openclaw'")
        except Exception:
            pass

        self._initBots()

    def _initBots(self):
        skillsJson = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "skills.json")
        if not os.path.isfile(skillsJson):
            return
        with open(skillsJson, "r", encoding="utf-8") as f:
            skills = json.load(f)
        for skill in skills:
            self.upsertBot(botId=skill["code"], name=skill["name"], role="skill", avatar=skill.get("icon"), managerId=skill.get("type"), status=skill.get("desc"))

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.dbPath)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()):
        with self._conn() as conn:
            conn.execute(sql, params)

    def fetchOne(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return _rowToDict(row)

    def fetchAll(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return _rowsToDicts(rows)

    def upsertBot(self, botId: str, name: str, role: str = 'pm', avatar: str = None, managerId: str = None, status: str = None):
        self.execute(
            "INSERT INTO bots (botId, name, role, avatar, managerId, status) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(botId) DO UPDATE SET "
            "name=excluded.name, role=excluded.role, "
            "avatar=COALESCE(excluded.avatar, bots.avatar), "
            "managerId=excluded.managerId, "
            "status=excluded.status",
            (botId, name, role, avatar, managerId, status)
        )

    def getBot(self, botId: str) -> Optional[Dict[str, Any]]:
        return self.fetchOne("SELECT * FROM bots WHERE botId = ? AND deleted = 0", (botId,))

    def getSubBots(self, managerId: str) -> List[Dict[str, Any]]:
        return self.fetchAll("SELECT * FROM bots WHERE managerId = ? AND deleted = 0", (managerId,))

    def getBotsByRole(self, role: str) -> List[Dict[str, Any]]:
        return self.fetchAll("SELECT * FROM bots WHERE role = ? AND deleted = 0", (role,))

    def getAllBots(self) -> List[Dict[str, Any]]:
        return self.fetchAll("SELECT * FROM bots WHERE deleted = 0 ORDER BY createTime")

    def updateBotStatus(self, botId: str, status: str, progress: int = None):
        now = int(time.time())
        if progress is not None:
            self.execute("UPDATE bots SET status = ?, progress = ?, lastTime = ? WHERE botId = ?", (status, progress, now, botId))
        else:
            self.execute("UPDATE bots SET status = ?, lastTime = ? WHERE botId = ?", (status, now, botId))

    def touchBot(self, botId: str):
        now = int(time.time())
        self.execute("UPDATE bots SET lastTime = ? WHERE botId = ?", (now, botId))

    def deleteBot(self, botId: str):
        self.execute("UPDATE bots SET deleted = 1 WHERE botId = ?", (botId,))

    def addMessage(self, botId: str = None, senderId: str = '', role: str = 'user', content: str = ''):
        self.execute(
            "INSERT INTO messages (botId, senderId, role, content) VALUES (?, ?, ?, ?)",
            (botId, senderId, role, content)
        )

    def getMessages(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.fetchAll(
            "SELECT * FROM messages WHERE deleted = 0 ORDER BY createTime ASC LIMIT ?",
            (limit,)
        )

    def getRecentMessageContent(self, seconds: int = 10) -> List[str]:
        cutoff = int(time.time()) - seconds
        rows = self.fetchAll(
            "SELECT content FROM messages WHERE createTime >= ? AND deleted = 0 ORDER BY createTime DESC",
            (cutoff,)
        )
        return [r['content'] for r in rows if r.get('content')]

    def getBotMessages(self, botId: str, limit: int = 50) -> List[Dict[str, Any]]:
        messages = self.fetchAll(
            "SELECT * FROM messages WHERE botId = ? AND deleted = 0 ORDER BY createTime DESC LIMIT ?",
            (botId, limit)
        )
        bot = self.getBot(botId)
        if bot:
            for msg in messages:
                msg['botName'] = bot['name']
                msg['botAvatar'] = bot['avatar']
        return messages

    def deleteMessages(self):
        self.execute("UPDATE messages SET deleted = 1 WHERE 1")

    def clearMessagesByBotId(self, botId: str):
        self.execute("UPDATE messages SET deleted = 1 WHERE botId = ?", (botId,))

    def getSessionsByBotId(self, botId: str) -> List[Dict[str, Any]]:
        return self.fetchAll(
            "SELECT * FROM sessions WHERE botId = ? AND deleted = 0",
            (botId,)
        )

    def createSession(self, userId: str, botId: str, sessionKey: str) -> Dict[str, Any]:
        now = int(time.time())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (userId, botId, sessionKey, createTime, lastActive) VALUES (?, ?, ?, ?, ?)",
                (userId, botId, sessionKey, now, now)
            )
        return {"userId": userId, "botId": botId, "sessionKey": sessionKey, "status": "active",
                "createTime": now, "lastActive": now}

    def getSession(self, userId: str, botId: str) -> Optional[Dict[str, Any]]:
        return self.fetchOne(
            "SELECT * FROM sessions WHERE userId = ? AND botId = ? AND status = 'active' AND deleted = 0",
            (userId, botId)
        )

    def updateSessionKey(self, userId: str, botId: str, sessionKey: str):
        now = int(time.time())
        self.execute(
            "UPDATE sessions SET sessionKey = ?, lastActive = ? WHERE userId = ? AND botId = ? AND status = 'active'",
            (sessionKey, now, userId, botId)
        )

    def getOpenclawSession(self) -> Optional[Dict[str, Any]]:
        return self.fetchOne(
            "SELECT * FROM sessions WHERE userId = 'openclaw' AND botId = 'openclaw' AND status = 'active' AND deleted = 0",
        )

    def getSessionByKey(self, sessionKey: str) -> Optional[Dict[str, Any]]:
        return self.fetchOne(
            "SELECT * FROM sessions WHERE sessionKey = ? AND status = 'active' AND deleted = 0",
            (sessionKey,)
        )

    def touchSessionByKey(self, sessionKey: str):
        now = int(time.time())
        self.execute("UPDATE sessions SET lastActive = ? WHERE sessionKey = ? AND status = 'active'", (now, sessionKey))

    def closeSession(self, userId: str):
        self.execute("UPDATE sessions SET status = 'closed' WHERE userId = ? AND status = 'active'", (userId,))

    def closeSessionByKey(self, sessionKey: str):
        self.execute("UPDATE sessions SET status = 'closed' WHERE sessionKey = ? AND status = 'active'", (sessionKey,))

    def getIdleSessions(self, timeoutSeconds: int) -> List[Dict[str, Any]]:
        cutoff = int(time.time()) - timeoutSeconds
        return self.fetchAll(
            "SELECT * FROM sessions WHERE status = 'active' AND lastActive < ? AND deleted = 0",
            (cutoff,)
        )

    def getAllActiveSessions(self) -> List[Dict[str, Any]]:
        return self.fetchAll(
            "SELECT * FROM sessions WHERE status = 'active' AND deleted = 0 ORDER BY lastActive DESC"
        )

    def getActiveChats(self, limit: int = 1000) -> List[Dict[str, Any]]:
        bots = self.fetchAll("""
        SELECT   b.botId,
                 b.name,
                 b.avatar,
                 b.role,
                 t.lastTime,
                 t.lastContent
          FROM (
              SELECT m.botId,
                     m.createTime AS lastTime,
                     SUBSTR(m.content, 1, 20) AS lastContent
              FROM messages m
              WHERE m.rowid IN (
                  SELECT MAX(rowid)
                  FROM messages
                  WHERE deleted = 0
                  GROUP BY botId
              )
              ORDER BY m.createTime DESC
              LIMIT ?
          ) AS t
          INNER JOIN bots b ON b.botId = t.botId
          ORDER BY t.lastTime DESC
        """, (limit,))
        return bots

    def getLastUserMessage(self, userId: str, botId: str) -> Optional[str]:
        row = self.fetchOne(
            "SELECT content FROM messages WHERE botId = ? AND role = 'user' AND deleted = 0 ORDER BY createTime DESC LIMIT 1",
            (botId,)
        )
        return row.get('content') if row else None
