#!/usr/bin/env python3
"""
Performance test for file upload/download functionality.
Tests the performance requirements specified in Prompt 10:
- File upload/download should handle 10MB files within ≤15 seconds
- File list should load within ≤2 seconds for 100+ files
"""

import os
import sys
import time
import tempfile
import uuid
from io import BytesIO
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ops_backend.settings')
import django
django.setup()

from apps.core.models import (
    Organization, Client, Project, Role, Permission, Attachment
)

User = get_user_model()


class FilePerformanceTestCase(TransactionTestCase):
    """Performance tests for file upload/download functionality."""

    def setUp(self):
        """Set up test data."""
        # Create test organization
        self.organization = Organization.objects.create(
            name='Test Performance Organization',
            organization_type='educational',
            email='test@performance.com'
        )

        # Create test client
        self.client_obj = Client.objects.create(
            organization=self.organization,
            client_since='2023-01-01',
            school_name='Performance Test School',
            contact_person='Test Contact',
            email='contact@performance.com',
            phone_whatsapp='1234567890'
        )

        # Create test project
        self.project = Project.objects.create(
            project_name='Performance Test Project',
            project_code='PERF001',
            client=self.client_obj,
            service_type='web_development',
            status='development',
            start_date='2023-01-01'
        )

        # Create test roles and permissions
        self.staff_role = Role.objects.create(
            name='Staff',
            codename='staff',
            description='Staff member role'
        )

        self.permission = Permission.objects.create(
            name='Upload Files',
            codename='upload_files',
            description='Permission to upload files'
        )
        self.staff_role.permissions.add(self.permission)

        # Create test user
        self.staff_user = User.objects.create_user(
            username='perf_test_user',
            email='perf@test.com',
            password='testpass123',
            employee_id='PERF001',
            role=self.staff_role
        )

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff_user)

    def create_test_file(self, size_mb=10, filename='test_performance.pdf'):
        """Create a test file of specified size in MB."""
        size_bytes = size_mb * 1024 * 1024
        content = b'0' * size_bytes
        
        return SimpleUploadedFile(
            filename,
            content,
            content_type='application/pdf'
        )

    def test_upload_10mb_file_performance(self):
        """Test that 10MB file upload completes within 15 seconds."""
        print("\n=== Testing 10MB File Upload Performance ===")
        
        # Create 10MB test file
        test_file = self.create_test_file(size_mb=10, filename='test_10mb.pdf')
        
        # Measure upload time
        start_time = time.time()
        
        response = self.client.post('/api/attachments/', {
            'file': test_file,
            'project_id': str(self.project.id),
            'description': 'Performance test file - 10MB'
        })
        
        end_time = time.time()
        upload_time = end_time - start_time
        
        print(f"Upload time: {upload_time:.2f} seconds")
        print(f"File size: 10MB")
        print(f"Upload speed: {10/upload_time:.2f} MB/s")
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertLessEqual(upload_time, 15.0, 
                           f"Upload took {upload_time:.2f}s, should be ≤15s")
        
        # Verify file was created
        attachment = Attachment.objects.get(id=response.data['id'])
        self.assertEqual(attachment.file_size, 10 * 1024 * 1024)
        self.assertEqual(attachment.file_name, 'test_10mb.pdf')
        
        print(f"✅ Upload performance test passed: {upload_time:.2f}s")
        
        return attachment

    def test_download_10mb_file_performance(self):
        """Test that 10MB file download completes within 15 seconds."""
        print("\n=== Testing 10MB File Download Performance ===")
        
        # First upload a 10MB file
        attachment = self.test_upload_10mb_file_performance()
        
        # Measure download time
        start_time = time.time()
        
        response = self.client.get(f'/api/attachments/{attachment.id}/download/')
        
        end_time = time.time()
        download_time = end_time - start_time
        
        print(f"Download time: {download_time:.2f} seconds")
        print(f"File size: 10MB")
        print(f"Download speed: {10/download_time:.2f} MB/s")
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(download_time, 15.0, 
                           f"Download took {download_time:.2f}s, should be ≤15s")
        
        # Verify file content
        self.assertEqual(len(response.content), 10 * 1024 * 1024)
        
        print(f"✅ Download performance test passed: {download_time:.2f}s")

    def test_file_list_performance_with_many_files(self):
        """Test that file list loads within 2 seconds for 100+ files."""
        print("\n=== Testing File List Performance with Many Files ===")
        
        # Create 100 small test files
        print("Creating 100 test files...")
        attachments = []
        for i in range(100):
            test_file = self.create_test_file(size_mb=0.1, filename=f'test_file_{i}.pdf')
            
            response = self.client.post('/api/attachments/', {
                'file': test_file,
                'project_id': str(self.project.id),
                'description': f'Performance test file {i}'
            })
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            attachments.append(response.data['id'])
        
        print(f"Created {len(attachments)} files")
        
        # Measure list loading time
        start_time = time.time()
        
        response = self.client.get('/api/attachments/by_project/', {
            'project_id': str(self.project.id)
        })
        
        end_time = time.time()
        list_time = end_time - start_time
        
        print(f"File list load time: {list_time:.2f} seconds")
        print(f"Number of files: {len(response.data)}")
        print(f"Files per second: {len(response.data)/list_time:.2f}")
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 100)
        self.assertLessEqual(list_time, 2.0, 
                           f"File list took {list_time:.2f}s, should be ≤2s")
        
        print(f"✅ File list performance test passed: {list_time:.2f}s")

    def test_concurrent_uploads_performance(self):
        """Test concurrent upload performance."""
        print("\n=== Testing Concurrent Upload Performance ===")
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def upload_file(file_index):
            """Upload a file and record the result."""
            try:
                test_file = self.create_test_file(
                    size_mb=1, 
                    filename=f'concurrent_test_{file_index}.pdf'
                )
                
                start_time = time.time()
                
                response = self.client.post('/api/attachments/', {
                    'file': test_file,
                    'project_id': str(self.project.id),
                    'description': f'Concurrent test file {file_index}'
                })
                
                end_time = time.time()
                upload_time = end_time - start_time
                
                results.put({
                    'success': response.status_code == status.HTTP_201_CREATED,
                    'time': upload_time,
                    'file_index': file_index
                })
                
            except Exception as e:
                results.put({
                    'success': False,
                    'error': str(e),
                    'file_index': file_index
                })
        
        # Start 5 concurrent uploads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=upload_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        concurrent_results = []
        while not results.empty():
            concurrent_results.append(results.get())
        
        # Analyze results
        successful_uploads = [r for r in concurrent_results if r['success']]
        failed_uploads = [r for r in concurrent_results if not r['success']]
        
        if successful_uploads:
            avg_time = sum(r['time'] for r in successful_uploads) / len(successful_uploads)
            max_time = max(r['time'] for r in successful_uploads)
            min_time = min(r['time'] for r in successful_uploads)
            
            print(f"Successful uploads: {len(successful_uploads)}/5")
            print(f"Average upload time: {avg_time:.2f}s")
            print(f"Min upload time: {min_time:.2f}s")
            print(f"Max upload time: {max_time:.2f}s")
            
            self.assertGreaterEqual(len(successful_uploads), 4, 
                                  "At least 4 out of 5 concurrent uploads should succeed")
            self.assertLessEqual(max_time, 15.0, 
                               f"Max upload time {max_time:.2f}s should be ≤15s")
        
        if failed_uploads:
            print(f"Failed uploads: {len(failed_uploads)}")
            for failure in failed_uploads:
                print(f"  File {failure['file_index']}: {failure.get('error', 'Unknown error')}")
        
        print(f"✅ Concurrent upload performance test completed")

    def test_file_validation_performance(self):
        """Test file validation performance with various file types."""
        print("\n=== Testing File Validation Performance ===")
        
        test_cases = [
            {'size_mb': 0.1, 'filename': 'small.pdf', 'expected_time': 1.0},
            {'size_mb': 1, 'filename': 'medium.pdf', 'expected_time': 2.0},
            {'size_mb': 5, 'filename': 'large.pdf', 'expected_time': 8.0},
            {'size_mb': 10, 'filename': 'xlarge.pdf', 'expected_time': 15.0},
        ]
        
        for test_case in test_cases:
            print(f"\nTesting {test_case['size_mb']}MB file...")
            
            test_file = self.create_test_file(
                size_mb=test_case['size_mb'], 
                filename=test_case['filename']
            )
            
            start_time = time.time()
            
            response = self.client.post('/api/attachments/', {
                'file': test_file,
                'project_id': str(self.project.id),
                'description': f'Validation test - {test_case["size_mb"]}MB'
            })
            
            end_time = time.time()
            upload_time = end_time - start_time
            
            print(f"  Upload time: {upload_time:.2f}s (expected: ≤{test_case['expected_time']}s)")
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertLessEqual(upload_time, test_case['expected_time'],
                               f"{test_case['size_mb']}MB upload took {upload_time:.2f}s, "
                               f"should be ≤{test_case['expected_time']}s")
            
            print(f"  ✅ {test_case['size_mb']}MB file validation passed")

    def run_all_performance_tests(self):
        """Run all performance tests and provide summary."""
        print("=" * 60)
        print("FILE MANAGEMENT PERFORMANCE TESTS")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Run individual performance tests
            self.test_upload_10mb_file_performance()
            self.test_download_10mb_file_performance()
            self.test_file_list_performance_with_many_files()
            self.test_concurrent_uploads_performance()
            self.test_file_validation_performance()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print("\n" + "=" * 60)
            print("PERFORMANCE TEST SUMMARY")
            print("=" * 60)
            print(f"Total test execution time: {total_time:.2f} seconds")
            print("✅ All performance tests passed!")
            print("\nPerformance Requirements Met:")
            print("- 10MB file upload: ≤15 seconds ✅")
            print("- 10MB file download: ≤15 seconds ✅")
            print("- File list with 100+ files: ≤2 seconds ✅")
            print("- Concurrent uploads: ≤15 seconds each ✅")
            print("- File validation: Within expected timeframes ✅")
            
        except Exception as e:
            print(f"\n❌ Performance test failed: {e}")
            raise


def main():
    """Run performance tests."""
    test_case = FilePerformanceTestCase()
    test_case.setUp()
    
    try:
        test_case.run_all_performance_tests()
    except Exception as e:
        print(f"Performance tests failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
