"""WebSocket consumer for the realtime Kanban board (Module 5)."""
import json

from channels.generic.websocket import AsyncWebsocketConsumer

from core.realtime import kanban_group


class KanbanConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user:
            await self.close(code=4001)
            return
        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        self.group = kanban_group(self.project_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def board_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
