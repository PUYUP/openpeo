from django.urls import path, re_path, include

# Channels
from apps.commerce.consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/chats/<uuid:chat_uuid>/messages/', ChatConsumer),
]
