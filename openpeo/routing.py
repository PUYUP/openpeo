from urllib.parse import parse_qs

from django.db import close_old_connections
from django.contrib.auth import get_user_model

from channels.db import database_sync_to_async
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.generals import get_model
from apps.commerce.routing import websocket_urlpatterns as commerce_websocket

User = get_model('person', 'User')


@database_sync_to_async
def get_user(token):
    # jwt = JWTAuthentication()
    # validated_token = jwt.get_validated_token(token)
    # user = jwt.get_user(validated_token)
    print(type(token))
    print(token)
    user = User.objects.get(id=token)

    if user:
        return user
    return None


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return TokenAuthMiddlewareInstance(scope, self)


class TokenAuthMiddlewareInstance:
    """
    Yeah, this is black magic:
    https://github.com/django/channels/issues/1399
    """
    def __init__(self, scope, middleware):
        self.middleware = middleware
        self.scope = dict(scope)
        self.inner = self.middleware.inner

    async def __call__(self, receive, send):
        query_param = parse_qs(self.scope['query_string'])
 
        # close old connection
        close_old_connections()

        # check JWT token
        # then authenticated user
        # :token set in request param
        if b'token' in query_param:
            token = query_param[b'token'][0].decode('utf-8')
            if token:
                self.scope['user'] = await get_user(token)

        inner = self.inner(self.scope)
        return await inner(receive, send)


TokenAuthMiddlewareStack = lambda inner: TokenAuthMiddleware(AuthMiddlewareStack(inner))


application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket': AllowedHostsOriginValidator(
        TokenAuthMiddlewareStack(
            URLRouter(
                commerce_websocket
            )
        )
    ),
})
