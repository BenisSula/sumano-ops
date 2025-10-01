"""
Authentication URL patterns for Sumano OMS.

This module defines URL patterns for authentication endpoints including
login, registration, profile management, and security monitoring.
"""

from django.urls import path, include
from rest_framework_simplejwt.views import TokenBlacklistView
from apps.core.views.auth import (
    CustomTokenObtainPairView, CustomTokenRefreshView,
    LoginView, LogoutView, UserRegistrationView,
    UserProfileView, ChangePasswordView, UserListView,
    RoleListView, SecurityEventListView, SecurityEventDetailView,
    resolve_security_events, security_statistics
)

app_name = 'auth'

urlpatterns = [
    # JWT Token endpoints
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    
    # Session-based authentication
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # User management
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('users/', UserListView.as_view(), name='user_list'),
    
    # Role management
    path('roles/', RoleListView.as_view(), name='role_list'),
    
    # Security monitoring
    path('security/events/', SecurityEventListView.as_view(), name='security_event_list'),
    path('security/events/<uuid:pk>/', SecurityEventDetailView.as_view(), name='security_event_detail'),
    path('security/events/resolve/', resolve_security_events, name='resolve_security_events'),
    path('security/statistics/', security_statistics, name='security_statistics'),
]
