from django.views import View
from django.shortcuts import render

from utils.generals import get_model

User = get_model('person', 'User')


class ChatView(View):
    template_name = 'chat.html'
    context = dict()

    def get(self, request):
        user = User.objects.all()[0].username
        return render(request, self.template_name, self.context)


class RoomView(View):
    template_name = 'room.html'
    context = dict()

    def get(self, request, room_name):
        self.context['room_name'] = room_name
        return render(request, self.template_name, self.context)
