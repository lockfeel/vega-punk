import re

from starlette.websockets import WebSocket

from service.gateway import SessionManager, OpenClawGatewayClient
from service.utils.common_util import getSkillName
from service.utils.db_util import DBase


class ChatHandler:

    def __init__(self, websocket: WebSocket, sessionManager: SessionManager, gatewayClient: OpenClawGatewayClient, db: DBase):
        self.currSession = None
        self.sessionKey = None
        self.websocket = websocket
        self.accumulatedText = ''
        self.handoffCache: set = set()
        self.sessionManager = sessionManager
        self.db = db
        self.gatewayClient = gatewayClient

    async def handle(self, payload: dict):
        stream = payload.get('stream')
        data = payload.get('data', {})

        if 'HEARTBEAT' in data.get('text', ''):
            return

        self.sessionKey = payload.get('sessionKey', '')
        self.currSession = self.sessionManager.getBySessionKey(self.sessionKey) if self.sessionManager else None
        if self.currSession:
            self.sessionManager.activeBySession(self.sessionKey)

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
            self.db.addMessage(
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
        # 已经在当前 skill 的 session 中，无需 handoff
        if self.currSession and self.currSession.botId == skillName:
            return

        self.handoffCache.add(skillName)
        await self._doHandoff(payload, skillName)

    async def _doHandoff(self, payload: dict, skillName: str):
        if not self.currSession:
            return

        skillSession = await self.sessionManager.getOrCreate(self.currSession.userId, skillName)
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

        lastUserMsg = self.db.getLastUserMessage(self.currSession.userId, self.currSession.botId)
        handoffMsg = f"请接管处理以下请求：\n\n{lastUserMsg}" if lastUserMsg else "请根据 SKILL 描述开始工作"
        await self.gatewayClient.sendChat(
            skillSession.sessionKey,
            handoffMsg,
            idempotencyKey=f"handoff-{skillName}-{payload.get('runId')}"
        )

    async def _sendJson(self, data: dict):
        try:
            await self.websocket.send_json(data)
        except Exception:
            pass
