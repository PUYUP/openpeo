from rest_framework import permissions


class IsCreatorOrReject(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # current user_uuid compared with creator uuid
        return request.user.uuid == obj.user.uuid
