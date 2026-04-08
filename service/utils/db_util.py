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
                    skills TEXT,
                    managerId TEXT,
                    status TEXT DEFAULT 'idle',
                    progress INTEGER DEFAULT 0,
                    createTime INTEGER DEFAULT (strftime('%s', 'now')),
                    deleted INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'draft',
                    progress INTEGER DEFAULT 0,
                    assigneeIds TEXT,
                    createTime INTEGER DEFAULT (strftime('%s', 'now')),
                    updateTime INTEGER DEFAULT (strftime('%s', 'now')),
                    deleted INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    planId INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    assignee TEXT,
                    status TEXT DEFAULT 'pending',
                    dependsOn TEXT,
                    result TEXT,
                    createTime INTEGER DEFAULT (strftime('%s', 'now')),
                    updateTime INTEGER DEFAULT (strftime('%s', 'now')),
                    deleted INTEGER DEFAULT 0,
                    FOREIGN KEY (planId) REFERENCES plans(id)
                );

                CREATE TABLE IF NOT EXISTS task_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    botId TEXT NOT NULL,
                    taskId INTEGER,
                    content TEXT,
                    type TEXT DEFAULT 'progress',
                    createTime INTEGER DEFAULT (strftime('%s', 'now'))
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    planId INTEGER,
                    senderId TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    createTime INTEGER DEFAULT (strftime('%s', 'now')),
                    deleted INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_bots_manager ON bots(managerId);

                CREATE INDEX IF NOT EXISTS idx_tasks_plan ON tasks(planId, status);
                CREATE INDEX IF NOT EXISTS idx_task_logs_task ON task_logs(taskId, createTime);
                CREATE INDEX IF NOT EXISTS idx_task_logs_bot ON task_logs(botId, createTime);
                CREATE INDEX IF NOT EXISTS idx_messages_plan ON messages(planId, createTime);
                CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(senderId, createTime);
                CREATE INDEX IF NOT EXISTS idx_bots_manager ON bots(managerId);
                CREATE TABLE IF NOT EXISTS sessions (
                    userId TEXT NOT NULL,
                    sessionKey TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    createTime INTEGER DEFAULT (strftime('%s', 'now')),
                    lastActive INTEGER DEFAULT (strftime('%s', 'now')),
                    deleted INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(userId, status);
                CREATE INDEX IF NOT EXISTS idx_sessions_key ON sessions(sessionKey);
                CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(status, lastActive);

                CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee, status);
            """)

        self._initBots()

    def _initBots(self):
        bots = [
            ("plan-executor", "执行星使", "https://res.amemo.cn/executing-plans.png"),
            ("branch-landing", "分支卫士", "https://res.amemo.cn/finishing-a-development-branch.png"),
            ("plan-builder", "规划谋士", "https://res.amemo.cn/planning-with-json.png"),
            ("review-intake", "评审接引人", "https://res.amemo.cn/receiving-code-review.png"),
            ("review-request", "审阅使", "https://res.amemo.cn/requesting-code-review.png"),
            ("parallel-swarm", "并行大师", "https://res.amemo.cn/dispatching-parallel-agents.png"),
            ("task-dispatcher", "子代理官", "https://res.amemo.cn/subagent-driven-development.png"),
            ("root-cause", "系统调试师", "https://res.amemo.cn/systematic-debugging.png"),
            ("test-first", "测试驱动者", "https://res.amemo.cn/test-driven-development.png"),
            ("verify-gate", "验核先锋", "https://res.amemo.cn/verification-before-completion.png"),
            ("worktree-setup", "分支管家", "https://res.amemo.cn/using-git-worktrees.png"),
            ("agent-browser", "浏览器精灵", "https://res.amemo.cn/agent-browser.png"),
            ("algorithmic-art", "算法画师", "https://res.amemo.cn/algorithmic-art.png"),
            ("brand-guidelines", "品牌管家", "https://res.amemo.cn/brand-guidelines.png"),
            ("canvas-design", "画布设计师", "https://res.amemo.cn/canvas-design.png"),
            ("docx", "文档匠人", "https://res.amemo.cn/docx.png"),
            ("find-skills", "技能探知", "https://res.amemo.cn/find-skills.png"),
            ("flutter-lens", "Flutter透视", "https://res.amemo.cn/flutter-lens.png"),
            ("frontend-design", "前端筑梦师", "https://res.amemo.cn/frontend-design.png"),
            ("internal-comms", "内宣使者", "https://res.amemo.cn/internal-comms.png"),
            ("mcp-builder", "MCP建造师", "https://res.amemo.cn/mcp-builder.png"),
            ("pdf", "PDF圣手", "https://res.amemo.cn/pdf.png"),
            ("pptx", "演示大师", "https://res.amemo.cn/pptx.png"),
            ("self-improving-agent", "自省者", "https://res.amemo.cn/self-improving-agent.png"),
            ("skill-creator", "技能锻造师", "https://res.amemo.cn/skill-creator.png"),
            ("slack-gif-creator", "动态图匠", "https://res.amemo.cn/slack-gif-creator.png"),
            ("theme-factory", "主题工厂", "https://res.amemo.cn/theme-factory.png"),
            ("ui-ux-pro-max", "UI/UX极客", "https://res.amemo.cn/ui-ux-pro-max.png"),
            ("vega-punk", "慎思者", "https://res.amemo.cn/vega-punk.png"),
            ("xlsx", "表格圣手", "https://res.amemo.cn/xlsx.png"),
        ]
        for botId, name, avatar in bots:
            self.upsertBot(botId=botId, name=name, role="skill", avatar=avatar)

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

    def upsertBot(self, botId: str, name: str, role: str = 'pm', avatar: str = None,
                  skills: list = None, managerId: str = None):
        self.execute(
            "INSERT INTO bots (botId, name, role, avatar, skills, managerId, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'idle') "
            "ON CONFLICT(botId) DO UPDATE SET "
            "name=excluded.name, role=excluded.role, avatar=COALESCE(excluded.avatar, bots.avatar), "
            "skills=COALESCE(excluded.skills, bots.skills), managerId=COALESCE(excluded.managerId, bots.managerId)",
            (botId, name, role, avatar, json.dumps(skills) if skills else None, managerId)
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
        if progress is not None:
            self.execute("UPDATE bots SET status = ?, progress = ? WHERE botId = ?", (status, progress, botId))
        else:
            self.execute("UPDATE bots SET status = ? WHERE botId = ?", (status, botId))

    def deleteBot(self, botId: str):
        self.execute("UPDATE bots SET deleted = 1 WHERE botId = ?", (botId,))

    def createPlan(self, name: str, description: str = None, assigneeIds: list = None) -> Dict[str, Any]:
        now = int(time.time())
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO plans (name, description, assigneeIds, createTime, updateTime) VALUES (?, ?, ?, ?, ?)",
                (name, description, json.dumps(assigneeIds) if assigneeIds else None, now, now)
            )
            return {"id": cursor.lastrowid, "name": name, "description": description, "assigneeIds": assigneeIds,
                    "status": "draft", "progress": 0, "createTime": now, "updateTime": now}

    def getPlan(self, planId: int) -> Optional[Dict[str, Any]]:
        return self.fetchOne("SELECT * FROM plans WHERE id = ? AND deleted = 0", (planId,))

    def getAllPlans(self, status: str = None) -> List[Dict[str, Any]]:
        if status:
            return self.fetchAll("SELECT * FROM plans WHERE status = ? AND deleted = 0 ORDER BY updateTime DESC", (status,))
        return self.fetchAll("SELECT * FROM plans WHERE deleted = 0 ORDER BY updateTime DESC")

    def updatePlan(self, planId: int, **kwargs):
        fields = []
        values = []
        for k, v in kwargs.items():
            fields.append(f"{k} = ?")
            values.append(json.dumps(v) if isinstance(v, list) else v)
        fields.append("updateTime = ?")
        values.append(int(time.time()))
        values.append(planId)
        self.execute(f"UPDATE plans SET {', '.join(fields)} WHERE id = ?", tuple(values))

    def deletePlan(self, planId: int):
        self.execute("UPDATE plans SET deleted = 1 WHERE id = ?", (planId,))

    def createTask(self, planId: int, title: str, assignee: str = None,
                   description: str = None, dependsOn: str = None) -> Dict[str, Any]:
        now = int(time.time())
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (planId, title, description, assignee, dependsOn, createTime, updateTime) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (planId, title, description, assignee, dependsOn, now, now)
            )
            return {"id": cursor.lastrowid, "planId": planId, "title": title, "assignee": assignee,
                    "status": "pending", "dependsOn": dependsOn, "createTime": now, "updateTime": now}

    def getTask(self, taskId: int) -> Optional[Dict[str, Any]]:
        return self.fetchOne("SELECT * FROM tasks WHERE id = ? AND deleted = 0", (taskId,))

    def getPlanTasks(self, planId: int) -> List[Dict[str, Any]]:
        return self.fetchAll("SELECT * FROM tasks WHERE planId = ? AND deleted = 0 ORDER BY createTime", (planId,))

    def getBotTasks(self, assignee: str, status: str = None) -> List[Dict[str, Any]]:
        if status:
            return self.fetchAll(
                "SELECT * FROM tasks WHERE assignee = ? AND status = ? AND deleted = 0 ORDER BY updateTime DESC",
                (assignee, status)
            )
        return self.fetchAll(
            "SELECT * FROM tasks WHERE assignee = ? AND deleted = 0 ORDER BY updateTime DESC",
            (assignee,)
        )

    def getPendingTasks(self, planId: int) -> List[Dict[str, Any]]:
        return self.fetchAll(
            "SELECT * FROM tasks WHERE planId = ? AND status = 'pending' AND deleted = 0 ORDER BY createTime",
            (planId,)
        )

    def updateTask(self, taskId: int, **kwargs):
        fields = []
        values = []
        for k, v in kwargs.items():
            fields.append(f"{k} = ?")
            values.append(v)
        fields.append("updateTime = ?")
        values.append(int(time.time()))
        values.append(taskId)
        self.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", tuple(values))

    def deleteTask(self, taskId: int):
        self.execute("UPDATE tasks SET deleted = 1 WHERE id = ?", (taskId,))

    def addTaskLog(self, botId: str, taskId: int = None, content: str = '', type: str = 'progress'):
        self.execute(
            "INSERT INTO task_logs (botId, taskId, content, type) VALUES (?, ?, ?, ?)",
            (botId, taskId, content, type)
        )

    def getTaskLogs(self, taskId: int = None, botId: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        if taskId:
            return self.fetchAll(
                "SELECT * FROM task_logs WHERE taskId = ? ORDER BY createTime DESC LIMIT ?",
                (taskId, limit)
            )
        if botId:
            return self.fetchAll(
                "SELECT * FROM task_logs WHERE botId = ? ORDER BY createTime DESC LIMIT ?",
                (botId, limit)
            )
        return []

    def addMessage(self, planId: int = None, senderId: str = '', role: str = 'user', content: str = ''):
        self.execute(
            "INSERT INTO messages (planId, senderId, role, content) VALUES (?, ?, ?, ?)",
            (planId, senderId, role, content)
        )

    def getMessages(self, planId: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        if planId:
            return self.fetchAll(
                "SELECT * FROM messages WHERE planId = ? AND deleted = 0 ORDER BY createTime ASC LIMIT ?",
                (planId, limit)
            )
        return self.fetchAll(
            "SELECT * FROM messages WHERE deleted = 0 ORDER BY createTime ASC LIMIT ?",
            (limit,)
        )

    def getBotMessages(self, senderId: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.fetchAll(
            "SELECT * FROM messages WHERE senderId = ? AND deleted = 0 ORDER BY createTime DESC LIMIT ?",
            (senderId, limit)
        )

    def deleteMessages(self, planId: int = None):
        if planId:
            self.execute("UPDATE messages SET deleted = 1 WHERE planId = ?", (planId,))
        else:
            self.execute("UPDATE messages SET deleted = 1 WHERE 1")

    def createSession(self, userId: str, sessionKey: str) -> Dict[str, Any]:
        now = int(time.time())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (userId, sessionKey, createTime, lastActive) VALUES (?, ?, ?, ?)",
                (userId, sessionKey, now, now)
            )
        return {"userId": userId, "sessionKey": sessionKey, "status": "active",
                "createTime": now, "lastActive": now}

    def getSession(self, userId: str) -> Optional[Dict[str, Any]]:
        return self.fetchOne(
            "SELECT * FROM sessions WHERE userId = ? AND status = 'active' AND deleted = 0",
            (userId,)
        )

    def getSessionByKey(self, sessionKey: str) -> Optional[Dict[str, Any]]:
        return self.fetchOne(
            "SELECT * FROM sessions WHERE sessionKey = ? AND status = 'active' AND deleted = 0",
            (sessionKey,)
        )

    def touchSession(self, userId: str):
        now = int(time.time())
        self.execute("UPDATE sessions SET lastActive = ? WHERE userId = ? AND status = 'active'", (now, userId))

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
