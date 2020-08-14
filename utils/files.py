import os
import calendar
import time
import datetime

from django.core.files.storage import FileSystemStorage
from django.template.defaultfilters import slugify


class FileSystemStorageExtend(FileSystemStorage):
    def generate_filename(self, filename, *args, **kwargs):
        # Format [timestamp]-[entity]-[object_uuid]-[filename].[ext]
        # Output: 12345675-media-99-mountain.jpg
        dirname, filename = os.path.split(filename)
        file_root, file_ext = os.path.splitext(filename)

        instance = kwargs.get('instance', None)
        content_type = slugify(instance.content_type)
        content_object = instance.content_object
        object_uuid = instance.uuid
        timestamp = calendar.timegm(time.gmtime())
        filename = '{0}_{1}_{2}_{3}'.format(
            timestamp, content_type, object_uuid, file_root)

        return os.path.normpath(
            os.path.join(
                dirname, self.get_valid_name(slugify(filename)+file_ext)))


def directory_image_path(instance, filename):
    fs = FileSystemStorageExtend()
    year = datetime.date.today().year
    month = datetime.date.today().month
    filename = fs.generate_filename(filename, instance=instance)

    # Will be 'files/2019/10/filename.jpg
    return 'images/{0}/{1}/{2}'.format(year, month, filename)


def directory_file_path(instance, filename):
    fs = FileSystemStorageExtend()
    year = datetime.date.today().year
    month = datetime.date.today().month
    filename = fs.generate_filename(filename, instance=instance)

    # Will be 'files/2019/10/filename.jpg
    return 'files/{0}/{1}/{2}'.format(year, month, filename)


def material_upload_path(instance, filename):
    fs = FileSystemStorageExtend()
    year = datetime.date.today().year
    month = datetime.date.today().month
    filename = fs.generate_filename(filename, instance=instance)
    dir_path = instance.lecture.material_type

    # Will be 'files/2019/10/video/filename.mp4
    return 'materials/{0}/{1}/{2}/{3}'.format(year, month, filename, dir_path)
