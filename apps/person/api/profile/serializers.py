import os
import base64

from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.core.files.base import ContentFile

from rest_framework import serializers

from utils.generals import get_model

Profile = get_model('person', 'Profile')


def handle_upload_profile_picture(instance, file, is_original=False):
    if instance and file:
        name, ext = os.path.splitext(file.name)
        username = instance.user.username

        if is_original:
            instance.picture_original.save('%s_original_%s' % (username, ext), file, save=False)
            instance.save(update_fields=['picture_original'])
        else:
            instance.picture.save('%s%s' % (username, ext), file, save=False)
            instance.save(update_fields=['picture'])


def base64_to_file(picture_base64):
    picture_format, picture_imgstr = picture_base64.split(';base64,') 
    picture_ext = picture_format.split('/')[-1] 
    picture_file = ContentFile(base64.b64decode(picture_imgstr), name='temp.' + picture_ext)
    return picture_file


# User profile serializer
class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField()

    class Meta:
        model = Profile
        exclude = ('user', 'id', 'create_date', 'update_date',)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['gender'] = instance.get_gender_display()
        return ret

    def to_internal_value(self, data):
        # process base64 image back to file
        picture_base64 = data.get('picture', None)
        picture_original_base64 = data.get('picture_original', None)
        picture_changed = data.get('picture_changed', False)
        picture_removed = data.get('picture_removed', False)

        # cropped picture
        if picture_base64 and isinstance(picture_base64, str):
            data['picture'] = base64_to_file(picture_base64)

        # original picture
        if picture_original_base64 and isinstance(picture_original_base64, str):
            data['picture_original'] = base64_to_file(picture_original_base64)

        data = super().to_internal_value(data)

        # user select new picture?
        if picture_changed:
            data['picture_changed'] = picture_changed

        # is picture changed?
        if picture_base64 :
            data['has_picture'] = True

        # is picture remove?
        if picture_removed:
            data['picture_removed'] = True
        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get('request', None)

        # upload picture / avatar use celery task
        picture = validated_data.pop('picture', None)
        picture_original = validated_data.pop('picture_original', None)
        picture_changed = validated_data.pop('picture_changed', False)
        picture_removed = validated_data.pop('picture_removed', False)
        has_picture = validated_data.pop('has_picture', False)

        # only execute if update has picture
        if has_picture or picture_removed:
            # cropped picture
            if picture:
                fsize = picture.size
                fname = picture.name

                # max size 2.5 MB
                if fsize > 312500:
                    raise serializers.ValidationError(_(u"Maksimal ukuran file 2.5 MB"))

                # only accept JPG, JPEG & PNG
                if not fname.endswith('.jpg') and not fname.endswith('.jpeg') and not fname.endswith('.png'):
                    raise serializers.ValidationError(_(u"File hanya boleh .jpg dan .png"))

                file = request.FILES.get('picture', None)
                if file is None:
                    file = picture
                handle_upload_profile_picture(instance, file)
            else:
                # delete picture
                instance.picture.delete(save=True)

            # original picture
            if picture_original and picture_changed:
                file = request.FILES.get('picture_original', None)
                if file is None:
                    file = picture_original
                handle_upload_profile_picture(instance, file, True)

            if not picture_original and not picture:
                # delete picture
                instance.picture_original.delete(save=True)

        # update user instance
        first_name = validated_data.pop('first_name', None)
        if first_name:
            instance.user.first_name = first_name
            instance.user.save()

        # this is real profile instance
        update_fields = list()
        for key, value in validated_data.items():
            if hasattr(instance, key):
                old_value = getattr(instance, key, None)
                if value and old_value != value:
                    update_fields.append(key)
                    setattr(instance, key, value)
        
        if update_fields:
            instance.save(update_fields=update_fields)
        return instance
