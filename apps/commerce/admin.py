from django.contrib import admin

from utils.generals import get_model

# Register your models here.
Bank = get_model('commerce', 'Bank')

admin.site.register(Bank)
