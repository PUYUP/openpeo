import logging
from typing import Awaitable, Final, List, TYPE_CHECKING, TypedDict

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.blacklist.exceptions import MissingToken

if TYPE_CHECKING:
    # If you're using a type checker, change this line to whatever your user model is.
    from authentication.models import CustomUser

logger = logging.getLogger(__name__)


TOKEN_STR_PREFIX: Final = "Bearer"


class Scope(TypedDict, total=False):
    subprotocols: List[str]


class QueryAuthMiddleware:
    """
    Middleware for django-channels that gets the user from a websocket subprotocol
    containing the JWT.
    """

    def __init__(self, inner):
        # Store the ASGI application we were passed
        self.inner = inner

    def __call__(self, scope: Scope):
        return QueryAuthMiddlewareInstance(scope, self)


class QueryAuthMiddlewareInstance:
    """
    Inner class that is instantiated once per scope.
    """

    def __init__(self, scope: Scope, middleware):
        self.middleware = middleware
        self.scope = dict(scope)
        self.inner = self.middleware.inner

    async def __call__(self, receive, send):
        if not self.scope.get("user") or self.scope["user"].is_anonymous:
            logger.debug("Attempting to authenticate user.")
            try:
                self.scope["user"] = await get_user_from_scope(self.scope)
                if "auth_error" in self.scope:
                    del self.scope["auth_error"]
            except (AuthenticationFailed, MissingTokenError) as e:
                self.scope["user"] = AnonymousUser()
                # Saves the error received during authentication into the scope so 
                # that we can do something with it later if we want.
                self.scope["auth_error"] = str(e)
                logger.info("Could not auth user: %s", str(e))

        inner = self.inner(self.scope)
        return await inner(receive, send)


JWTBearerProtocolAuthStack = lambda inner: QueryAuthMiddleware(
    AuthMiddlewareStack(inner)
)


def get_bearer_subprotocol(scope: Scope):
    for subproto in scope.get("subprotocols", []):
        if subproto.startswith(TOKEN_STR_PREFIX):
            return subproto


class JWTAuth(JSONWebTokenAuthentication):
    @classmethod
    def get_token_from_request(cls, scope: Scope) -> str:
        """
        Abuse this method to get token from django-channels scope instead of an http
        request.
        :param scope: Scope from django-channels middleware.
        """
        token_string = get_bearer_subprotocol(scope)
        if not token_string:
            raise MissingToken("No token provided.")
        token = token_string.split(TOKEN_STR_PREFIX)[1]
        return token


class MissingTokenError(Exception):
    pass


@database_sync_to_async
def get_user_from_scope(scope) -> Awaitable[CustomUser]:
    auth = JWTAuth()
    authenticated = auth.authenticate(scope)

    if authenticated is None:
        raise MissingTokenError("Cannot find token in scope.")

    user, token = authenticated

    logger.debug("Authenticated %s", user)

    return user
