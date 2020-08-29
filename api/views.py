# THIRD PARTY
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import AllowAny


class RootApiView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        return Response({
            'person': {
                'token': reverse('person:token_obtain_pair', request=request,
                                 format=format, current_app='person'),
                'token-refresh': reverse('person:token_refresh', request=request,
                                         format=format, current_app='person'),
                'users': reverse('person:user-list', request=request,
                                 format=format, current_app='person'),
                'otps': reverse('person:otp-list', request=request,
                                format=format, current_app='person'),
            },
            'commerce': {
                'banks': reverse('commerce:bank-list', request=request,
                                 format=format, current_app='commerce'),
                'payment-banks': reverse('commerce:payment-bank-list', request=request,
                                         format=format, current_app='commerce'),
                'products': reverse('commerce:product-list', request=request,
                                    format=format, current_app='commerce'),
                'carts': reverse('commerce:cart-list', request=request,
                                 format=format, current_app='commerce'),
                'orders': reverse('commerce:order-list', request=request,
                                  format=format, current_app='commerce'),
                'sells': reverse('commerce:sell-list', request=request,
                                 format=format, current_app='commerce'),
                'address': reverse('commerce:address-list', request=request,
                                   format=format, current_app='commerce'),
            }
        })
