"""
Permission classes for Sumano OMS RBAC system.

This module provides DRF permission classes that enforce role-based
access control and security event logging.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from apps.core.models import User, Role, Permission
from apps.core.services.security_service import SecurityService


class IsAuthenticatedUser(IsAuthenticated):
    """
    Permission class that requires user authentication.
    
    This is the base permission class that all other permissions inherit from.
    It ensures users are authenticated and logs security events.
    """
    
    def has_permission(self, request: Request, view) -> bool:
        """Check if user is authenticated."""
        if not super().has_permission(request, view):
            # Log unauthorized access attempt
            SecurityService.log_security_event(
                event_type='access_denied',
                user=None,
                ip_address=SecurityService.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                details={'reason': 'not_authenticated'},
                severity='medium'
            )
            return False
        
        return True


class HasRole(BasePermission):
    """
    Permission class that requires user to have a specific role.
    
    This permission class checks if the authenticated user has
    the required role(s) to access the resource.
    """
    
    required_roles = []
    require_all_roles = False  # If True, user must have ALL roles; if False, ANY role
    
    def has_permission(self, request: Request, view) -> bool:
        """Check if user has required role(s)."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user = request.user
        
        # Get user's roles (primary + additional)
        user_roles = []
        if user.role:
            user_roles.append(user.role.codename)
        user_roles.extend([role.codename for role in user.additional_roles.all()])
        
        # Check role requirements
        if self.require_all_roles:
            has_permission = all(role in user_roles for role in self.required_roles)
        else:
            has_permission = any(role in user_roles for role in self.required_roles)
        
        if not has_permission:
            # Log access denied
            SecurityService.log_security_event(
                event_type='access_denied',
                user=user,
                ip_address=SecurityService.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                details={
                    'reason': 'insufficient_role',
                    'required_roles': self.required_roles,
                    'user_roles': user_roles
                },
                severity='medium'
            )
        
        return has_permission


class HasPermission(BasePermission):
    """
    Permission class that requires user to have specific permissions.
    
    This permission class checks if the authenticated user has
    the required permissions to access the resource.
    """
    
    required_permissions = []
    require_all_permissions = False  # If True, user must have ALL permissions; if False, ANY permission
    
    def has_permission(self, request: Request, view) -> bool:
        """Check if user has required permission(s)."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user = request.user
        
        # Get user's permission codenames
        user_permission_codenames = [p.codename for p in user.get_all_permissions()]
        
        # Check permission requirements
        if self.require_all_permissions:
            has_permission = all(perm in user_permission_codenames for perm in self.required_permissions)
        else:
            has_permission = any(perm in user_permission_codenames for perm in self.required_permissions)
        
        if not has_permission:
            # Log access denied
            SecurityService.log_security_event(
                event_type='access_denied',
                user=user,
                ip_address=SecurityService.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                details={
                    'reason': 'insufficient_permission',
                    'required_permissions': self.required_permissions,
                    'user_permissions': user_permission_codenames
                },
                severity='medium'
            )
        
        return has_permission


class IsSuperAdmin(HasRole):
    """Permission class that requires superadmin role."""
    required_roles = ['superadmin']


class IsStaff(HasRole):
    """Permission class that requires staff role."""
    required_roles = ['staff', 'superadmin']


class IsClientContact(HasRole):
    """Permission class that requires client_contact role."""
    required_roles = ['client_contact']


class IsAuditor(HasRole):
    """Permission class that requires auditor role."""
    required_roles = ['auditor', 'superadmin']


class CanManageProjects(HasPermission):
    """Permission class that requires project management permissions."""
    required_permissions = ['core.manage_projects']


class CanViewProjects(HasPermission):
    """Permission class that requires project view permissions."""
    required_permissions = ['core.view_projects']


class CanManageClients(HasPermission):
    """Permission class that requires client management permissions."""
    required_permissions = ['core.manage_clients']


class CanViewClients(HasPermission):
    """Permission class that requires client view permissions."""
    required_permissions = ['core.view_clients']


class CanManageUsers(HasPermission):
    """Permission class that requires user management permissions."""
    required_permissions = ['core.manage_users']


class CanViewUsers(HasPermission):
    """Permission class that requires user view permissions."""
    required_permissions = ['view_users']


class CanManageSecurityEvents(HasPermission):
    """Permission class that requires security event management permissions."""
    required_permissions = ['core.manage_security_events']


class CanViewSecurityEvents(HasPermission):
    """Permission class that requires security event view permissions."""
    required_permissions = ['view_security_events']


class CanViewDocuments(HasPermission):
    """Permission class that requires document view permissions."""
    required_permissions = ['view_documents']


class CanManageDocuments(HasPermission):
    """Permission class that requires document management permissions."""
    required_permissions = ['manage_documents']


class CanApproveDocuments(HasPermission):
    """Permission class that requires document approval permissions."""
    required_permissions = ['approve_documents']


class ReadOnlyForAuthenticated(BasePermission):
    """
    Permission class that allows read-only access for authenticated users.
    
    This is useful for endpoints that should be accessible to all
    authenticated users but only allow read operations.
    """
    
    def has_permission(self, request: Request, view) -> bool:
        """Check if user can perform the requested action."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read operations (GET, HEAD, OPTIONS)
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Log write operation attempt
        SecurityService.log_security_event(
            event_type='access_denied',
            user=request.user,
            ip_address=SecurityService.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            details={'reason': 'read_only_endpoint'},
            severity='low'
        )
        
        return False
