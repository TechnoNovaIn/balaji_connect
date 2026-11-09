from rest_framework import permissions

class IsActiveEmployee(permissions.BasePermission):
    """
    Allows access only to authenticated, active employees.
    Disabled employees immediately lose access.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsAdminRole(permissions.BasePermission):
    """
    Allows access only to active Administrators.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active and 
            request.user.is_administrator
        )


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Allows users to edit their own profile, or administrators to edit any profile.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_administrator:
            return True
        return obj == request.user


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins to edit/delete it.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        
        # Read permissions are allowed to any active employee
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.is_administrator:
            return True

        # Check for common ownership attributes
        if hasattr(obj, 'author'):
            return obj.author == request.user
        if hasattr(obj, 'uploader'):
            return obj.uploader == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False

