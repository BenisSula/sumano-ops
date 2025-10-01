#!/usr/bin/env python
"""
Verification script for the unified document system.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ops_backend.settings')
django.setup()

from apps.core.models import DocumentTemplate, DocumentInstance
from apps.core.services.pdf_service import PDFGenerationService
from django.contrib.auth import get_user_model

User = get_user_model()

def main():
    print("=== DOCUMENT SYSTEM VERIFICATION ===")
    
    # Check template count
    total_templates = DocumentTemplate.objects.count()
    published_templates = DocumentTemplate.objects.filter(status='PUBLISHED').count()
    
    print(f"Total templates: {total_templates}")
    print(f"Published templates: {published_templates}")
    
    # Check document instances
    total_documents = DocumentInstance.objects.count()
    print(f"Total document instances: {total_documents}")
    
    # List template types
    template_types = DocumentTemplate.objects.values_list('template_type', flat=True).distinct()
    print(f"Available template types: {list(template_types)}")
    
    # Test PDF generation with a real template
    template = DocumentTemplate.objects.filter(status='PUBLISHED').first()
    if template:
        print(f"\n=== TESTING PDF GENERATION ===")
        print(f"Using template: {template.name} ({template.template_type})")
        
        try:
            user = User.objects.first()
            if not user:
                print("ERROR: No users found in database")
                return
            
            # Generate a test document
            doc_instance = PDFGenerationService.generate_from_template(
                template_name=template.name,
                data={
                    'title': 'Verification Test Document',
                    'content': 'This is a test document generated during system verification.',
                    'project_name': 'System Verification Project',
                    'client_name': 'Test Client'
                },
                created_by_user=user
            )
            
            print(f"✅ Successfully generated document: {doc_instance.document_title}")
            print(f"   Document ID: {doc_instance.id}")
            print(f"   Document status: {doc_instance.status}")
            print(f"   PDF file exists: {bool(doc_instance.generated_pdf)}")
            print(f"   Document number: {doc_instance.document_number}")
            
            # Check file size
            if doc_instance.generated_pdf:
                try:
                    file_size = doc_instance.get_file_size()
                    print(f"   PDF file size: {file_size} bytes")
                except Exception as e:
                    print(f"   Could not get file size: {e}")
            
        except Exception as e:
            print(f"❌ PDF generation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No published templates found")
    
    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == '__main__':
    main()
