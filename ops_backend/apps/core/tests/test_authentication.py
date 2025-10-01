"""
Authentication and authorization tests for Sumano OMS.

This module contains comprehensive tests for the authentication system,
RBAC functionality, and security event logging.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from apps.core.models import Role, Permission, SecurityEvent, Organization, Client as ClientModel
from apps.core.services.security_service import SecurityService

User = get_user_model()


class AuthenticationBackendTestCase(TestCase):
    """Test authentication backends functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Organization",
            organization_type="business",
            email="contact@testorg.com"
        )
        
        self.client_model = ClientModel.objects.create(
            organization=self.organization,
            client_since="2023-01-01"
        )
        
        # Create test roles
        self.staff_role = Role.objects.get(codename='staff')
        self.superadmin_role = Role.objects.get(codename='superadmin')
        
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            employee_id='EMP001',
            role=self.staff_role
        )
        
        self.superuser = User.objects.create_user(
            username='superuser',
            email='admin@example.com',
            password='adminpass123',
            first_name='Super',
            last_name='User',
            employee_id='EMP002',
            role=self.superadmin_role
        )
        
        self.client = Client()
    
    def test_successful_login(self):
        """Test successful user login."""
        response = self.client.post('/admin/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Should redirect on successful login
        self.assertEqual(response.status_code, 302)
        
        # Check that security event was logged
        security_events = SecurityEvent.objects.filter(
            event_type='login_success',
            user=self.user
        )
        self.assertTrue(security_events.exists())
    
    def test_failed_login(self):
        """Test failed login attempt."""
        response = self.client.post('/admin/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # Check that security event was logged
        security_events = SecurityEvent.objects.filter(
            event_type='login_failure',
            user=self.user
        )
        self.assertTrue(security_events.exists())
        
        # Check that failed login attempts were incremented
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)
    
    def test_account_lockout(self):
        """Test account lockout after multiple failed attempts."""
        # Simulate multiple failed login attempts
        for i in range(6):  # More than the default limit
            self.client.post('/admin/login/', {
                'username': 'testuser',
                'password': 'wrongpassword'
            })
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_account_locked())
        
        # Try to login with correct password while locked
        response = self.client.post('/admin/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Should still fail due to lockout
        self.assertEqual(response.status_code, 200)
        
        # Check that lockout event was logged
        lockout_events = SecurityEvent.objects.filter(
            event_type='access_denied',
            user=self.user,
            details__contains={'reason': 'account_locked'}
        )
        self.assertTrue(lockout_events.exists())


class RBACPermissionTestCase(APITestCase):
    """Test RBAC permission system."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Organization",
            organization_type="business",
            email="contact@testorg.com"
        )
        
        self.client_model = ClientModel.objects.create(
            organization=self.organization,
            client_since="2023-01-01"
        )
        
        # Get roles
        self.staff_role = Role.objects.get(codename='staff')
        self.superadmin_role = Role.objects.get(codename='superadmin')
        self.client_contact_role = Role.objects.get(codename='client_contact')
        
        # Create test users
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='staffpass123',
            first_name='Staff',
            last_name='User',
            employee_id='EMP003',
            role=self.staff_role
        )
        
        self.superadmin_user = User.objects.create_user(
            username='superadmin',
            email='admin@example.com',
            password='adminpass123',
            first_name='Super',
            last_name='Admin',
            employee_id='EMP004',
            role=self.superadmin_role
        )
        
        self.client_user = User.objects.create_user(
            username='clientuser',
            email='client@example.com',
            password='clientpass123',
            first_name='Client',
            last_name='User',
            employee_id='EMP005',
            role=self.client_contact_role
        )
        
        self.api_client = APIClient()
    
    def test_jwt_token_authentication(self):
        """Test JWT token authentication."""
        # Test token obtain
        response = self.api_client.post('/api/auth/token/', {
            'username': 'staffuser',
            'password': 'staffpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Test protected endpoint with token
        token = response.data['access']
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.api_client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'staffuser')
    
    def test_staff_user_permissions(self):
        """Test staff user permissions."""
        # Get JWT token
        response = self.api_client.post('/api/auth/token/', {
            'username': 'staffuser',
            'password': 'staffpass123'
        })
        token = response.data['access']
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Staff should be able to view users
        response = self.api_client.get('/api/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Staff should be able to view roles
        response = self.api_client.get('/api/auth/roles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_client_contact_permissions(self):
        """Test client contact user permissions."""
        # Get JWT token
        response = self.api_client.post('/api/auth/token/', {
            'username': 'clientuser',
            'password': 'clientpass123'
        })
        token = response.data['access']
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Client contact should NOT be able to view users
        response = self.api_client.get('/api/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Client contact should be able to view their profile
        response = self.api_client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_superadmin_permissions(self):
        """Test superadmin permissions."""
        # Get JWT token
        response = self.api_client.post('/api/auth/token/', {
            'username': 'superadmin',
            'password': 'adminpass123'
        })
        token = response.data['access']
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Superadmin should be able to view security events
        response = self.api_client.get('/api/auth/security/events/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Superadmin should be able to view users
        response = self.api_client.get('/api/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to protected endpoints."""
        # Try to access protected endpoint without token
        response = self.api_client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to access with invalid token
        self.api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = self.api_client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SecurityEventLoggingTestCase(APITestCase):
    """Test security event logging functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Organization",
            organization_type="business",
            email="contact@testorg.com"
        )
        
        self.client_model = ClientModel.objects.create(
            organization=self.organization,
            client_since="2023-01-01"
        )
        
        self.staff_role = Role.objects.get(codename='staff')
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            employee_id='EMP006',
            role=self.staff_role
        )
        
        self.api_client = APIClient()
    
    def test_login_security_events(self):
        """Test that login events are properly logged."""
        # Test successful login
        response = self.api_client.post('/api/auth/token/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that login events were logged
        login_attempt_events = SecurityEvent.objects.filter(
            event_type='login_attempt',
            user=None  # Before authentication
        )
        self.assertTrue(login_attempt_events.exists())
        
        login_success_events = SecurityEvent.objects.filter(
            event_type='login_success',
            user=self.user
        )
        self.assertTrue(login_success_events.exists())
        
        # Test failed login
        response = self.api_client.post('/api/auth/token/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Check that failure event was logged
        login_failure_events = SecurityEvent.objects.filter(
            event_type='login_failure',
            user=self.user
        )
        self.assertTrue(login_failure_events.exists())
    
    def test_access_denied_events(self):
        """Test that access denied events are logged."""
        # Get token for staff user
        response = self.api_client.post('/api/auth/token/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to access superadmin-only endpoint
        response = self.api_client.get('/api/auth/security/events/')
        
        # Should be forbidden for staff user
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Check that access denied event was logged
        access_denied_events = SecurityEvent.objects.filter(
            event_type='access_denied',
            user=self.user
        )
        self.assertTrue(access_denied_events.exists())
    
    def test_security_statistics(self):
        """Test security statistics functionality."""
        # Create some security events
        SecurityService.log_security_event(
            event_type='login_attempt',
            user=None,
            ip_address='127.0.0.1',
            details={'test': 'data'}
        )
        
        SecurityService.log_security_event(
            event_type='login_success',
            user=self.user,
            ip_address='127.0.0.1',
            details={'test': 'data'}
        )
        
        # Get statistics
        stats = SecurityService.get_security_statistics(days=7)
        
        self.assertEqual(stats['total_events'], 2)
        self.assertEqual(stats['login_attempts'], 1)
        self.assertEqual(stats['login_successes'], 1)
        self.assertEqual(stats['login_failures'], 0)


class UserRegistrationTestCase(APITestCase):
    """Test user registration functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.api_client = APIClient()
    
    def test_user_registration(self):
        """Test user registration endpoint."""
        registration_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'phone': '+1234567890',
            'department': 'development'
        }
        
        response = self.api_client.post('/api/auth/register/', registration_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        
        # Check that user has default role (staff)
        self.assertEqual(user.role.codename, 'staff')
        
        # Check that registration event was logged
        registration_events = SecurityEvent.objects.filter(
            event_type='login_attempt',  # Using login_attempt as closest match
            user=user,
            details__contains={'action': 'user_registration'}
        )
        self.assertTrue(registration_events.exists())
    
    def test_registration_validation(self):
        """Test user registration validation."""
        # Test password mismatch
        registration_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123',
            'password_confirm': 'differentpass123'
        }
        
        response = self.api_client.post('/api/auth/register/', registration_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        
        # Test duplicate username
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='pass123'
        )
        
        registration_data = {
            'username': 'existinguser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        
        response = self.api_client.post('/api/auth/register/', registration_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)


class PasswordChangeTestCase(APITestCase):
    """Test password change functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Organization",
            organization_type="business",
            email="contact@testorg.com"
        )
        
        self.client_model = ClientModel.objects.create(
            organization=self.organization,
            client_since="2023-01-01"
        )
        
        self.staff_role = Role.objects.get(codename='staff')
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123',
            first_name='Test',
            last_name='User',
            employee_id='EMP007',
            role=self.staff_role
        )
        
        self.api_client = APIClient()
        
        # Get JWT token
        response = self.api_client.post('/api/auth/token/', {
            'username': 'testuser',
            'password': 'oldpass123'
        })
        self.token = response.data['access']
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_password_change(self):
        """Test successful password change."""
        change_data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        response = self.api_client.post('/api/auth/change-password/', change_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that password change event was logged
        password_change_events = SecurityEvent.objects.filter(
            event_type='password_change',
            user=self.user
        )
        self.assertTrue(password_change_events.exists())
        
        # Verify new password works
        response = self.api_client.post('/api/auth/token/', {
            'username': 'testuser',
            'password': 'newpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_password_change_validation(self):
        """Test password change validation."""
        # Test wrong old password
        change_data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        response = self.api_client.post('/api/auth/change-password/', change_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)
        
        # Test password mismatch
        change_data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass123'
        }
        
        response = self.api_client.post('/api/auth/change-password/', change_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
