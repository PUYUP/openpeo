from rest_framework import serializers

from utils.generals import get_model

Notification = get_model('commerce', 'Notification')


class NotificationSerializer(serializers.ModelSerializer):
    chat_uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)
        ret['actor_uuid'] = instance.actor.uuid
        ret['recipient_uuid'] = instance.recipient.uuid

        if instance.action_object_content_type and instance.action_object:
            model_name = instance.action_object_content_type.model
            action_object = instance.action_object

            ret['model_name'] = model_name

            # order item
            if model_name == 'orderitem' and action_object:
                ret['object'] = {
                    'id': action_object.id,
                    'uuid': action_object.uuid,
                    'name': action_object.product.name,
                    'price': action_object.product.price,
                    'is_creator': action_object.product.user.id == request.user.id,
                    
            }

        return ret
