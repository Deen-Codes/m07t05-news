"""DRF permission classes for role-based API access."""

from rest_framework import permissions


SAFE_METHODS = permissions.SAFE_METHODS


def _is_in_group(user, group_name):
    """Return True if user is authenticated and in the named group."""
    return (
        user
        and user.is_authenticated
        and user.groups.filter(name=group_name).exists()
    )


class IsJournalistOrReadOnly(permissions.BasePermission):
    """Allow safe methods for anyone, writes only for journalists."""

    message = 'Only journalists may create or modify articles.'

    def has_permission(self, request, view):
        """Safe verbs open to anyone, writes only for journalists."""
        if request.method in SAFE_METHODS:
            return True
        return _is_in_group(request.user, 'Journalist')


class IsEditorOrJournalistForWrites(permissions.BasePermission):
    """Reads are public; writes require the Editor or Journalist role."""

    message = 'Only editors or journalists may modify articles.'

    def has_permission(self, request, view):
        """Apply the read/write split described in the class docstring."""
        if request.method in SAFE_METHODS:
            return True
        return (
            _is_in_group(request.user, 'Editor')
            or _is_in_group(request.user, 'Journalist')
        )


class IsEditor(permissions.BasePermission):
    """Permit access only to authenticated users in the Editor group."""

    message = 'Only editors may approve articles.'

    def has_permission(self, request, view):
        """Return ``True`` only for authenticated users in the Editor group."""
        return _is_in_group(request.user, 'Editor')
