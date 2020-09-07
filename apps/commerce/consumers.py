import json

from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer

from utils.generals import get_model

User = get_model('person', 'User')

from pprint import pprint


class ChatMessagesConsumer(AsyncWebsocketConsumer):
    """Consumer to manage WebSocket connections for the Notification app,
    called when the websocket is handshaking as part of initial connection.
    """

    async def connect(self):
        """Consumer Connect implementation, to validate user status and prevent
        non authenticated user to take advante from the connection."""
        self.chat_uuid = self.scope['url_route']['kwargs']['chat_uuid']
        self.chat_channel = 'chat_%s' % self.chat_uuid

        if self.scope['user'].is_anonymous:
            # Reject the connection
            await self.close()

        else:
            # Accept the connection
            await self.channel_layer.group_add('chat_messages', self.chat_channel)
            await self.accept()

    async def disconnect(self, close_code):
        """Consumer implementation to leave behind the group at the moment the
        closes the connection."""
        await self.channel_layer.group_discard('chat_messages', self.chat_channel)

    async def receive(self, text_data):
        """Receive method implementation to redirect any new message received
        on the websocket to broadcast to all the clients."""
        await self.send(text_data=json.dumps(text_data))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['chat_uuid']
        self.room_group_name = 'chat_%s' % self.room_name

        if self.scope['user'].is_anonymous:
            # Reject the connection
            await self.close()
        else:
            # Accept connection
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
