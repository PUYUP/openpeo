from django.db import transaction
from django.db.models import (
    Prefetch, Case, When, Value, BooleanField, Q, OuterRef, Subquery
)
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from rest_framework import viewsets, status as response_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, NotAcceptable
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser

from utils.generals import get_model
from apps.commerce.utils.permissions import IsCreatorOrReject
from apps.commerce.api.chat.serializers import (
    ChatSerializer, ChatMessageSerializer,
    ChatAttachmentSerializer
)

Chat = get_model('commerce', 'Chat')
ChatMessage = get_model('commerce', 'ChatMessage')
ChatAttachment = get_model('commerce', 'ChatAttachment')


class ChatApiView(viewsets.ViewSet):
    """
    POST
    --------------
        :chat_messages = optional
        :send_to_user = required

        {
            "chat_messages": [
                {"message": "LOL"}
            ],
            "send_to_user": 1
        }
    """
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)
    permission_action = {
        'list': [IsAuthenticated],
        'create': [IsAuthenticated],
        'destroy': [IsAuthenticated, IsCreatorOrReject],
    }

    def get_permissions(self):
        """
        Instantiates and returns
        the list of permissions that this view requires.
        """
        try:
            # return permission_classes depending on `action`
            return [permission() for permission in self.permission_action
                    [self.action]]
        except KeyError:
            # action is not set return default permission_classes
            return [permission() for permission in self.permission_classes]

    def list(self, request, format=None):
        context = {'request': request}
        messages = ChatMessage.objects \
            .prefetch_related(Prefetch('chat'), Prefetch('user'), Prefetch('content_type'), Prefetch('content_object')) \
            .select_related('chat', 'user', 'content_type', 'content_object') \
            .filter(chat__id=OuterRef('id'))

        queryset = Chat.objects \
            .prefetch_related(Prefetch('user'), Prefetch('send_to_user', 'user__profile')) \
            .select_related('user', 'send_to_user', 'user__profile') \
            .annotate(
                first_message=Subquery(messages.order_by('create_date').values('message')[:1]),
                last_message=Subquery(messages.order_by('-create_date').values('message')[:1]),
                last_message_date=Subquery(messages.order_by('-create_date').values('create_date')[:1]),
                last_message_sender=Subquery(messages.order_by('-create_date').values('user__username')[:1]),
                last_message_sender_uuid=Subquery(messages.order_by('-create_date').values('user__uuid')[:1])
            ) \
            .filter(Q(user_id=request.user.id) | Q(send_to_user__id=request.user.id)) \
            .order_by('-last_message_date')

        serializer = ChatSerializer(queryset, many=True, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def create(self, request, format=None):
        context = {'request': request}
        serializer = ChatSerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, uuid=None, format=None):
        context = {'request': self.request}

        # single object
        try:
            queryset = Chat.objects.get(Q(uuid=uuid), Q(user_id=request.user.id) | Q(send_to_user__id=request.user.id))
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        serializer = ChatSerializer(queryset, many=False, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def destroy(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = Chat.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        # execute delete
        queryset.delete()
        return Response({'detail': _("Delete success!")}, status=response_status.HTTP_204_NO_CONTENT)

    """#############
    CHAT MESSAGES
    #############"""
    # LIST, CREATE
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['get', 'post'], detail=True,
            permission_classes=[IsAuthenticated],
            url_path='messages', url_name='view_message')
    def view_message(self, request, uuid=None, format=None):
        """
        Params:
            {
                "message": "string",
                "chat": "chat id",
            }
        """
        context = {'request': request}
        method = request.method
        user = request.user

        if method == 'POST':
            try:
                chat_obj = Chat.objects.get(uuid=uuid)
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            except ObjectDoesNotExist:
                raise NotFound(_("Chat tidak ditemukan"))
            
            # set chat object
            context['chat'] = chat_obj

            serializer = ChatMessageSerializer(data=request.data, context=context)
            if serializer.is_valid(raise_exception=True):
                try:
                    serializer.save()
                except ValidationError as e:
                    return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
                return Response(serializer.data, status=response_status.HTTP_200_OK)
            return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

        elif method == 'GET':
            queryset = ChatMessage.objects.annotate(
                is_creator=Case(
                    When(Q(user__uuid=user.uuid), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            ) \
            .prefetch_related(Prefetch('chat'), Prefetch('user'), Prefetch('content_type')) \
            .select_related('chat', 'user', 'content_type') \
            .filter(chat__uuid=uuid).order_by('create_date')

            serializer = ChatMessageSerializer(queryset, many=True, context=context)
            return Response(serializer.data, status=response_status.HTTP_200_OK)

    # UPDATE, DELETE
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['patch', 'delete'], detail=True,
            permission_classes=[IsAuthenticated, IsCreatorOrReject],
            url_path='messages/(?P<message_uuid>[^/.]+)', 
            url_name='view_message_update')
    def view_message_update(self, request, uuid=None, message_uuid=None):
        """
        Params:
            {
                "message": "string"
            }
        """
        context = {'request': request}
        method = request.method

        try:
            queryset = ChatMessage.objects.get(uuid=message_uuid)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)
        
        if method == 'PATCH':
            serializer = ChatMessageSerializer(queryset, data=request.data, partial=True, context=context)
            if serializer.is_valid(raise_exception=True):
                try:
                    serializer.save()
                except ValidationError as e:
                    return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
                return Response(serializer.data, status=response_status.HTTP_200_OK)
            return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

        elif method == 'DELETE':
            # execute delete
            queryset.delete()
            return Response(
                {'detail': _("Delete success!")},
                status=response_status.HTTP_204_NO_CONTENT)

    """***********
    ATTACHMENT
    ***********"""
    # LIST, CREATE
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['get', 'post'], detail=True,
            permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser],
            url_path='attachments', url_name='view_attachment')
    def view_attachment(self, request, uuid=None):
        """
        Params:
            {
                "title": "string", [required]
                "description": "string",
                "attach_file": "file" [required]
            }
        """
        context = {'request': request}
        method = request.method
        user = request.user

        if method == 'POST':
            try:
                parent_instance = ChatMessage.objects.get(uuid=uuid)
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            except ObjectDoesNotExist:
                raise NotFound(_("Certificate not found"))

            context['parent_instance'] = parent_instance
            serializer = ChatAttachmentSerializer(data=request.data, context=context)
            if serializer.is_valid(raise_exception=True):
                try:
                    serializer.save()
                except ValidationError as e:
                    return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
                return Response(serializer.data, status=response_status.HTTP_200_OK)
            return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

        elif method == 'GET':
            try:
                queryset = ChatAttachment.objects.annotate(
                    is_creator=Case(
                        When(Q(certificate__user__uuid=user.uuid), then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField()
                    )
                ) \
                .prefetch_related(Prefetch('certificate'), Prefetch('certificate__user')) \
                .select_related('certificate', 'certificate__user') \
                .filter(certificate__uuid=uuid)
            except Exception as e:
                raise NotAcceptable(detail=_("Something wrong %s" % type(e)))

            serializer = ChatAttachmentSerializer(queryset, many=True, context=context)
            return Response(serializer.data, status=response_status.HTTP_200_OK)

    # UPDATE, DELETE
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['patch', 'delete'], detail=True,
            permission_classes=[IsAuthenticated],
            parser_classes=[MultiPartParser],
            url_path='attachments/(?P<attachment_uuid>[^/.]+)', 
            url_name='view_attachment_update')
    def view_attachment_update(self, request, uuid=None, attachment_uuid=None):
        """
        Params:
            {
                "title": "string",
                "description": "string",
                "attach_file": "file"
            }
        """
        context = {'request': request}
        method = request.method

        try:
            queryset = ChatAttachment.objects.get(uuid=attachment_uuid)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)
        
        if method == 'PATCH':
            serializer = ChatAttachmentSerializer(queryset, data=request.data, partial=True, context=context)
            if serializer.is_valid(raise_exception=True):
                try:
                    serializer.save()
                except ValidationError as e:
                    return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
                return Response(serializer.data, status=response_status.HTTP_200_OK)
            return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

        elif method == 'DELETE':
            # execute delete
            queryset.delete()
            return Response(
                {'detail': _("Delete success!")},
                status=response_status.HTTP_204_NO_CONTENT)
