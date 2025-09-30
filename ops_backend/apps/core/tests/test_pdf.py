"""
Tests for PDF generation endpoints.
"""
from django.test import TestCase, Client


class PDFTestCase(TestCase):
    """Test cases for PDF generation endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_pdf_status_endpoint(self):
        """Test PDF status endpoint."""
        response = self.client.get('/api/pdf/status/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['weasyprint_available'])
        self.assertIn('PDF generation is available', data['message'])
    
    def test_pdf_generation_endpoint(self):
        """Test PDF generation endpoint."""
        response = self.client.get('/api/pdf/test/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('ci-sample.pdf', response['Content-Disposition'])
        
        # Verify PDF content is not empty
        self.assertGreater(len(response.content), 1000)  # PDF should be reasonably sized
