from django.urls import path, include

from api.views import RootApiView

from apps.person.api import routers as person_routers
from apps.commerce.api import routers as commerce_routers

urlpatterns = [
    path('', RootApiView.as_view(), name='api'),
    path('person/', include((person_routers, 'person'), namespace='persons')),
    path('commerce/', include((commerce_routers, 'commerce'), namespace='commerces')),
]
