"""
Management command to test the complete Client Intake system end-to-end.

This command tests the full workflow from form submission to PDF generation.
"""

import logging
import time
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.core.models import Client, Organization, DocumentTemplate, DocumentInstance
from apps.core.services.pdf_service import PDFGenerationService

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the complete Client Intake system end-to-end'

    def add_arguments(self, parser):
        parser.add_argument(
            '--performance-test',
            action='store_true',
            help='Run performance test for form submission + PDF generation'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== CLIENT INTAKE SYSTEM TEST ==="))
        
        # Test 1: Create test data
        self.stdout.write("\n1. Creating test organization and client...")
        try:
            organization = Organization.objects.create(
                name='Test Elementary School',
                organization_type='educational',
                email='admin@testelementary.edu',
                phone='+1234567890',
                address_line1='123 School Street',
                city='Test City',
                state_province='TC',
                postal_code='12345',
                country='Test Country'
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Created organization: {organization.name}"))
            
            client = Client.objects.create(
                organization=organization,
                client_since=timezone.now().date(),
                relationship_status='prospect',
                school_name='Test Elementary School',
                contact_person='John Doe',
                role_position='Principal',
                email='john@testelementary.edu',
                phone_whatsapp='+1234567890',
                address='123 School Street, Test City, TC 12345',
                current_website='https://testelementary.edu',
                number_of_students=500,
                number_of_staff=50,
                project_type=['website_development', 'student_portal'],
                project_purpose=['improve_student_engagement', 'streamline_administration'],
                pilot_scope_features=['user_authentication', 'student_management', 'gradebook'],
                timeline_preference='asap',
                pilot_start_date=(timezone.now().date() + timedelta(days=30)),
                pilot_end_date=(timezone.now().date() + timedelta(days=180)),
                content_availability=True,
                token_commitment_fee=5000.00,
                additional_notes='This is a test school for the pilot project. We are excited to work with Sumano Tech.'
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Created client: {client.school_name}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to create test data: {e}"))
            return

        # Test 2: Verify client properties
        self.stdout.write("\n2. Testing client model properties...")
        try:
            self.stdout.write(f"   Intake completion: {client.is_intake_complete}")
            self.stdout.write(f"   Completion percentage: {client.intake_completion_percentage}%")
            
            if client.is_intake_complete:
                self.stdout.write(self.style.SUCCESS("✅ Intake form is complete"))
            else:
                self.stdout.write(self.style.WARNING("⚠️ Intake form is incomplete"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to test client properties: {e}"))

        # Test 3: PDF Generation
        self.stdout.write("\n3. Testing PDF generation...")
        try:
            # Get the intake template
            template = DocumentTemplate.objects.filter(
                name='Client Intake Form',
                status='PUBLISHED'
            ).first()
            
            if not template:
                self.stdout.write(self.style.ERROR("❌ No published intake template found"))
                return
            
            self.stdout.write(f"   Using template: {template.name}")
            
            # Prepare PDF data
            pdf_data = {
                'school_name': client.school_name,
                'contact_person': client.contact_person,
                'role_position': client.role_position,
                'email': client.email,
                'phone_whatsapp': client.phone_whatsapp,
                'address': client.address,
                'current_website': client.current_website,
                'number_of_students': str(client.number_of_students),
                'number_of_staff': str(client.number_of_staff),
                'project_type': ', '.join(client.project_type),
                'project_purpose': ', '.join(client.project_purpose),
                'pilot_scope_features': ', '.join(client.pilot_scope_features),
                'pilot_start_date': client.pilot_start_date.strftime('%Y-%m-%d') if client.pilot_start_date else '',
                'pilot_end_date': client.pilot_end_date.strftime('%Y-%m-%d') if client.pilot_end_date else '',
                'timeline_preference': client.get_timeline_preference_display(),
                'content_availability': 'Yes' if client.content_availability else 'No',
                'token_commitment_fee': str(client.token_commitment_fee),
                'additional_notes': client.additional_notes,
                'submission_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Generate PDF
            start_time = time.perf_counter()
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("❌ No users found in database"))
                return
            
            document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                template_name=template.name,
                data=pdf_data,
                user=user
            )
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            self.stdout.write(self.style.SUCCESS(f"✅ PDF generated successfully"))
            self.stdout.write(f"   Document ID: {document_instance.id}")
            self.stdout.write(f"   Document title: {document_instance.document_title}")
            self.stdout.write(f"   PDF size: {len(pdf_bytes)} bytes")
            self.stdout.write(f"   Generation time: {duration:.3f} seconds")
            
            # Check performance requirement (≤10 seconds)
            if duration <= 10:
                self.stdout.write(self.style.SUCCESS(f"✅ Performance requirement met (≤10s): {duration:.3f}s"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ Performance requirement exceeded: {duration:.3f}s > 10s"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ PDF generation failed: {e}"))

        # Test 4: Performance Test (if requested)
        if options['performance_test']:
            self.stdout.write("\n4. Running performance test...")
            try:
                performance_results = []
                num_tests = 5
                
                for i in range(num_tests):
                    start_time = time.perf_counter()
                    
                    # Generate PDF with same data
                    document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                        template_name=template.name,
                        data=pdf_data,
                        user=user
                    )
                    
                    end_time = time.perf_counter()
                    duration = end_time - start_time
                    performance_results.append(duration)
                    
                    self.stdout.write(f"   Test {i+1}: {duration:.3f}s")
                
                # Calculate statistics
                avg_duration = sum(performance_results) / len(performance_results)
                max_duration = max(performance_results)
                min_duration = min(performance_results)
                
                self.stdout.write(f"\n   Performance Statistics:")
                self.stdout.write(f"   Average: {avg_duration:.3f}s")
                self.stdout.write(f"   Maximum: {max_duration:.3f}s")
                self.stdout.write(f"   Minimum: {min_duration:.3f}s")
                
                if avg_duration <= 5:  # Target average ≤5 seconds
                    self.stdout.write(self.style.SUCCESS(f"✅ Performance target met (avg ≤5s): {avg_duration:.3f}s"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️ Performance target exceeded (avg >5s): {avg_duration:.3f}s"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Performance test failed: {e}"))

        # Test 5: Cleanup
        self.stdout.write("\n5. Cleaning up test data...")
        try:
            # Delete test documents
            DocumentInstance.objects.filter(
                document_title__icontains='Test Elementary School'
            ).delete()
            
            # Delete test client and organization
            client.delete()
            organization.delete()
            
            self.stdout.write(self.style.SUCCESS("✅ Test data cleaned up"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Cleanup failed: {e}"))

        self.stdout.write(self.style.SUCCESS("\n=== CLIENT INTAKE SYSTEM TEST COMPLETE ==="))
