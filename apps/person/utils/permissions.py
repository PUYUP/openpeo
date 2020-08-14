from rest_framework import permissions


class IsCurrentUserOrReject(permissions.BasePermission):
    def has_permission(self, request, view):
        # uuid from url param
        uuid = view.kwargs.get('uuid', 0)
        return uuid == str(request.user.uuid)
