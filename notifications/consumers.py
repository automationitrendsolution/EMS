"""WebSocket consumer for realtime per-user notifications (Module 11)."""
import json

from channels.generic.websocket import AsyncWebsocketConsumer

from core.realtime import user_group


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user:
            await self.close(code=4001)
            return
        self.group = user_group(str(user.id))
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify(self, event):
        await self.send(text_data=json.dumps({"type": "notification", **event["payload"]}))
