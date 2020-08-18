from rest_framework import permissions


class IsCurrentUserOrReject(permissions.BasePermission):
    def has_permission(self, request, view):
        # uuid from url param
        uuid = view.kwargs.get('uuid', 0)
        return uuid == str(request.user.uuid)


class IsCreatorOrReject(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # current user_uuid compared with creator uuid
        return request.user.uuid == obj.user.uuid
