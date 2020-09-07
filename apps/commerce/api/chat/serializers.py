from django.db import transaction
from django.db.models import Q, Prefetch
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from utils.generals import get_model
from apps.person.utils.auth import CurrentUserDefault
from apps.commerce.api.base.serializers import ProductSerializer

Chat = get_model('commerce', 'Chat')
ChatMessage = get_model('commerce', 'ChatMessage')


class ChatMessageSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    is_creator = serializers.BooleanField(read_only=True)

    class Meta:
        model = ChatMessage
        exclude = ('chat',)

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)

        # check current user create message is the creator
        if request.method == 'POST':
            ret['is_creator'] = instance.user.id == request.user.id
        ret['user_uuid'] = instance.user.uuid

        # content embeded?
        if instance.object_id and instance.content_type:
            model_name = instance.content_type.model
            content_object = instance.content_object

            ret['model_name'] = model_name

            if content_object:
                # product
                if model_name == 'product':
                    ret['product'] = {
                        'id': content_object.id,
                        'uuid': content_object.uuid,
                        'name': content_object.name,
                        'price': content_object.price,
                    }

                # orderitem
                if model_name == 'orderitem':
                    ret['orderitem'] = {
                        'id': content_object.id,
                        'uuid': content_object.uuid,
                        'status': content_object.status,
                        'order_uuid': content_object.order.uuid,
                    }

                    ret['product'] = {
                        'id': content_object.product.id,
                        'uuid': content_object.product.uuid,
                        'name': content_object.product.name,
                        'price': content_object.product.price,
                    }

        return ret

    @transaction.atomic
    def create(self, validated_data):
        chat = self.context.get('chat')
        chat_message, created = ChatMessage.objects.get_or_create(chat=chat, **validated_data)
        return chat_message


class ChatSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    url = serializers.HyperlinkedIdentityField(view_name='commerce:chat-detail',
                                               lookup_field='uuid', read_only=True)
    first_message = serializers.CharField(read_only=True)
    last_message = serializers.CharField(read_only=True)
    last_message_date = serializers.DateTimeField(read_only=True)
    last_message_sender = serializers.CharField(read_only=True)
    last_message_sender_uuid = serializers.CharField(read_only=True)

    chat_messages = ChatMessageSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Chat
        fields = '__all__'

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)
        send_to_username = request.user.username
        last_message_sender_uuid = None

        if hasattr(instance, 'last_message_sender_uuid'):
            last_message_sender_uuid = getattr(instance, 'last_message_sender_uuid')

        if str(request.user.uuid) == last_message_sender_uuid:
            send_to_username = _("Saya")
        else:
            if instance.send_to_user.id == request.user.id:
                send_to_username = instance.user.username
            else:
                send_to_username = instance.send_to_user.username

        ret['send_to_username'] = send_to_username
        return ret

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')

        # if user has chat or send chat by other user, just get the chat. Not created again.
        user = validated_data.pop('user')
        send_to_user = validated_data.pop('send_to_user')
        chat_messages = validated_data.pop('chat_messages')

        try:
            obj = Chat.objects \
                .prefetch_related(Prefetch('user'), Prefetch('send_to_user')) \
                .select_related('user', 'send_to_user') \
                .filter((Q(user_id=request.user.id) & Q(send_to_user__id=send_to_user.id))
                        | (Q(user_id=send_to_user.id) & Q(send_to_user__id=request.user.id))
            ).get()
        except ObjectDoesNotExist:
            obj = Chat.objects.create(user=user, send_to_user=send_to_user)

        # create message
        if chat_messages:
            for item in chat_messages:
                ChatMessage.objects.create(chat=obj, **item)

        return obj
