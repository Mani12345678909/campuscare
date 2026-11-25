from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import User


def role_required(*allowed_roles):
    """
    Decorator for views that checks if the logged-in user possesses one of the allowed roles
    or is a superuser.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(
                request,
                f"Access denied. Your role ({request.user.get_role_display()}) does not have permission to access this resource."
            )
            raise PermissionDenied("You do not have permission to view this resource.")
        return _wrapped_view
    return decorator


def student_required(view_func):
    return role_required(User.Role.STUDENT, User.Role.ADMIN)(view_func)


def faculty_required(view_func):
    return role_required(User.Role.FACULTY, User.Role.MANAGER, User.Role.ADMIN)(view_func)


def reporter_required(view_func):
    return role_required(User.Role.STUDENT, User.Role.FACULTY, User.Role.MANAGER, User.Role.ADMIN)(view_func)


def technician_required(view_func):
    return role_required(User.Role.TECHNICIAN, User.Role.MANAGER, User.Role.ADMIN)(view_func)


def manager_required(view_func):
    return role_required(User.Role.MANAGER, User.Role.ADMIN)(view_func)


def admin_required(view_func):
    return role_required(User.Role.ADMIN)(view_func)


def can_user_update_status(user, ticket):
    """
    - Managers and Admins can update any ticket.
    - Technicians can update tickets assigned to them or unassigned tickets.
    - Students / Faculty (Reporters) cannot update ticket status.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role in [User.Role.MANAGER, User.Role.ADMIN]:
        return True
    if user.role == User.Role.TECHNICIAN:
        return ticket.assigned_to == user or ticket.assigned_to is None
    return False


def can_user_assign_ticket(user):
    """
    Only Managers and Admins can assign or reassign tickets and change triage priority.
    """
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.role in [User.Role.MANAGER, User.Role.ADMIN]
