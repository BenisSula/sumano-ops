"""
Django management command to verify the document system.
"""
from django.core.management.base import BaseCommand
from apps.core.models import DocumentTemplate, DocumentInstance
from apps.core.services.pdf_service import PDFGenerationService
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Verify the unified document system functionality'

    def handle(self, *args, **options):
        self.stdout.write("=== DOCUMENT SYSTEM VERIFICATION ===")
        
        # Check template count
        total_templates = DocumentTemplate.objects.count()
        published_templates = DocumentTemplate.objects.filter(status='PUBLISHED').count()
        
        self.stdout.write(f"Total templates: {total_templates}")
        self.stdout.write(f"Published templates: {published_templates}")
        
        # Check document instances
        total_documents = DocumentInstance.objects.count()
        self.stdout.write(f"Total document instances: {total_documents}")
        
        # List template types
        template_types = DocumentTemplate.objects.values_list('template_type', flat=True).distinct()
        self.stdout.write(f"Available template types: {list(template_types)}")
        
        # Test PDF generation with a real template
        template = DocumentTemplate.objects.filter(status='PUBLISHED', template_type='INTAKE').first()
        if template:
            self.stdout.write(f"\n=== TESTING PDF GENERATION ===")
            self.stdout.write(f"Using template: {template.name} ({template.template_type})")
            
            try:
                user = User.objects.first()
                if not user:
                    self.stdout.write(self.style.ERROR("ERROR: No users found in database"))
                    return
                
                # Generate a test document with INTAKE template data
                doc_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                    template_name=template.name,
                    data={
                        'title': 'Verification Test Document',
                        'content': 'This is a test document generated during system verification.',
                        'company_name': 'Test Company',
                        'contact_name': 'Test Contact',
                        'email': 'test@example.com',
                        'project_type': 'Verification Test',
                        'description': 'System verification test document'
                    },
                    user=user
                )
                
                self.stdout.write(self.style.SUCCESS(f"✅ Successfully generated document: {doc_instance.document_title}"))
                self.stdout.write(f"   Document ID: {doc_instance.id}")
                self.stdout.write(f"   Document status: {doc_instance.status}")
                self.stdout.write(f"   PDF file exists: {bool(doc_instance.generated_pdf)}")
                self.stdout.write(f"   Document number: {doc_instance.document_number}")
                self.stdout.write(f"   PDF bytes generated: {len(pdf_bytes)} bytes")
                
                # Check file size
                if doc_instance.generated_pdf:
                    try:
                        file_size = doc_instance.get_file_size()
                        self.stdout.write(f"   PDF file size: {file_size} bytes")
                    except Exception as e:
                        self.stdout.write(f"   Could not get file size: {e}")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ PDF generation failed: {e}"))
        else:
            self.stdout.write(self.style.ERROR("❌ No published templates found"))
        
        self.stdout.write(self.style.SUCCESS("\n=== VERIFICATION COMPLETE ==="))
