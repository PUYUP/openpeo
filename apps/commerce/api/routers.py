from django.urls import path, include

from rest_framework.routers import DefaultRouter

from apps.commerce.api.base.views import (
    BankApiView, PaymentBankApiView, ProductApiView
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register('banks', BankApiView, basename='bank')
router.register('payment-banks', PaymentBankApiView, basename='payment-bank')
router.register('products', ProductApiView, basename='product')

app_name = 'commerce'

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]
