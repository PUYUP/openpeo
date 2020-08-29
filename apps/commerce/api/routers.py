from django.urls import path, include

from rest_framework.routers import DefaultRouter

from apps.commerce.api.base.views import (
    BankApiView, PaymentBankApiView, ProductApiView,
    DeliveryAddressApiView
)
from apps.commerce.api.transaction.views import (
    CartApiView, OrderApiView, SellApiView
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register('banks', BankApiView, basename='bank')
router.register('payment-banks', PaymentBankApiView, basename='payment-bank')
router.register('products', ProductApiView, basename='product')
router.register('carts', CartApiView, basename='cart')
router.register('orders', OrderApiView, basename='order')
router.register('sells', SellApiView, basename='sell')
router.register('address', DeliveryAddressApiView, basename='address')

app_name = 'commerce'

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]
