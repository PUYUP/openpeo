from django.conf import settings

broker_url = settings.REDIS_URL
broker_transport_options = {'visibility_timeout': 3600} 
result_backend = settings.REDIS_URL
task_serializer = 'json'
