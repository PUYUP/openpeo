from django.urls import path, include

# THIRD PARTY
from rest_framework.routers import DefaultRouter

# LOCAL
from apps.person.api.user.views import (
    TokenObtainPairViewExtend,
    TokenRefreshView,
    UserApiView
)
from apps.person.api.otp.views import OTPFactoryApiView

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register('users', UserApiView, basename='user')
router.register('otps', OTPFactoryApiView, basename='otp')

app_name = 'person'

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),

    path('token/', TokenObtainPairViewExtend.as_view(), name='token_obtain_pair'),
    path('token-refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
