from django.db.models import Q, Prefetch, Subquery, OuterRef

from rest_framework import viewsets, status as response_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from utils.generals import get_model
from apps.commerce.api.notification.serializers import NotificationSerializer

Notification = get_model('commerce', 'Notification')
OrderItem = get_model('commerce', 'OrderItem')
ChatMessage = get_model('commerce', 'ChatMessage')


class NotificationApiView(viewsets.ViewSet):
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)

    def list(self, request, format=None):
        context = {'request': request}

        chat_message = ChatMessage.objects \
            .filter(object_id=OuterRef('action_object_object_id'),
                    content_type=OuterRef('action_object_content_type'))

        queryset = Notification.objects \
            .prefetch_related(Prefetch('actor'), Prefetch('recipient'), Prefetch('action_object_content_type'),
                              Prefetch('action_object')) \
            .select_related('actor', 'recipient', 'action_object_content_type') \
            .annotate(
                chat_uuid=Subquery(chat_message.values('chat__uuid')[:1])
            ) \
            .filter(Q(recipient_id=request.user.id))
        
        serializer = NotificationSerializer(queryset, many=True, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)
