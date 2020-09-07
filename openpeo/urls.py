from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

from api import routers as api_routers

from views.chat import ChatView, RoomView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('chat/<str:room_name>/', RoomView.as_view(), name='room'),
    path('api/', include(api_routers)),
    path('admin/', admin.site.urls),
]

urlpatterns += static(settings.MEDIA_URL,
                      document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL,
                      document_root=settings.STATIC_ROOT)

# Remove admin sidebar nav sidebar
# https://docs.djangoproject.com/en/3.1/ref/contrib/admin/#django.contrib.admin.AdminSite.enable_nav_sidebar
admin.site.enable_nav_sidebar = False


if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
