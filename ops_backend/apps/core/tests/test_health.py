"""
Tests for health check endpoints.
"""
from django.test import TestCase, Client
from django.urls import reverse


class HealthCheckTestCase(TestCase):
    """Test cases for health check endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_health_check_endpoint(self):
        """Test basic health check endpoint."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'Sumano OMS Backend')
        self.assertEqual(data['version'], '0.1.0')
    
    def test_health_detailed_endpoint(self):
        """Test detailed health check endpoint."""
        response = self.client.get('/health/detailed/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'Sumano OMS Backend')
        self.assertEqual(data['version'], '0.1.0')
        self.assertIn('python_version', data)
        self.assertIn('django_version', data)
        self.assertIn('debug', data)
        self.assertIn('database', data)
