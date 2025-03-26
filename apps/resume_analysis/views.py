from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import default_storage
from django.conf import settings
import os
from .models import Resume, ResumeContent
from .services.document_processor import DocumentProcessor
from .services.text_extractor import TextExtractor
from .services.ocr_processor import OCRProcessor  # Make sure to import OCRProcessor
import logging

# Set up logging
logger = logging.getLogger(__name__)

@login_required
def upload_form(request):
    return render(request, 'resume_analysis/upload_form.html')

@login_required
def upload_resume(request):
    if request.method == 'POST':
        if 'resume' not in request.FILES:
            messages.error(request, 'Please select a file to upload')
            return redirect('accounts:dashboard')

        file = request.FILES['resume']
        
        # Validate file size
        if file.size > settings.MAX_UPLOAD_SIZE:
            messages.error(request, f'File size exceeds {settings.MAX_UPLOAD_SIZE/1024/1024}MB limit')
            return redirect('accounts:dashboard')

        # Get file extension
        file_extension = file.name.lower().split('.')[-1]
        
        # Map file extensions to content types
        content_type_map = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'tiff': 'image/tiff',
            'bmp': 'image/bmp'
        }

        # Check if file extension is supported
        if file_extension not in content_type_map:
            messages.error(request, 'Unsupported file type. Please upload PDF, Word documents, or images.')
            return redirect('accounts:dashboard')

        try:
            # Create resume record
            resume = Resume.objects.create(
                user=request.user,
                original_filename=file.name,
                status='processing'
            )

            # Save file
            file_path = os.path.join('resumes', str(resume.file_id), file.name)
            saved_path = default_storage.save(file_path, file)
            full_file_path = os.path.join(settings.MEDIA_ROOT, saved_path)

            # Process document
            text_extractor = TextExtractor()
            
            try:
                extracted_text = text_extractor.extract(file, file.name)
                
                if not extracted_text or len(extracted_text.strip()) < 50:
                    logger.warning(f"Insufficient text extracted from {file.name}, attempting OCR")
                    # Try OCR as fallback
                    ocr_processor = OCRProcessor()
                    extracted_text = ocr_processor.process_pdf_with_ocr(full_file_path)

                if not extracted_text or len(extracted_text.strip()) < 50:
                    raise ValueError("Could not extract sufficient text from the document")

                # Create resume content
                ResumeContent.objects.create(
                    resume=resume,
                    raw_text=extracted_text,
                    structured_data={}
                )

                resume.status = 'processed'
                resume.save()
                
                messages.success(request, 'Resume uploaded and processed successfully')

            except Exception as processing_error:
                logger.error(f"Error processing file {file.name}: {str(processing_error)}")
                resume.status = 'failed'
                resume.save()
                
                ResumeContent.objects.create(
                    resume=resume,
                    raw_text="Error processing document. Please ensure the file contains readable text.",
                    structured_data={'error': str(processing_error)}
                )
                
                messages.error(request, 'Failed to process the document. Please ensure the file contains readable text.')

            return redirect('accounts:dashboard')

        except Exception as e:
            logger.error(f"Error in upload process: {str(e)}")
            if resume:
                resume.status = 'failed'
                resume.save()
            messages.error(request, f'Error uploading resume: {str(e)}')
            return redirect('accounts:dashboard')

    return redirect('accounts:dashboard')

@login_required
def view_resume(request, file_id):
    resume = get_object_or_404(Resume, file_id=file_id, user=request.user)
    content = get_object_or_404(ResumeContent, resume=resume)
    
    context = {
        'resume': resume,
        'content': content,
        'error': content.structured_data.get('error', None) if resume.status == 'failed' else None
    }
    return render(request, 'resume_analysis/view_resume.html', context)

@login_required
def delete_resume(request, file_id):
    if request.method == 'POST':
        resume = get_object_or_404(Resume, file_id=file_id, user=request.user)
        
        # Delete file from storage
        file_path = os.path.join('resumes', str(resume.file_id), resume.original_filename)
        if default_storage.exists(file_path):
            default_storage.delete(file_path)
        
        # Delete database record
        resume.delete()
        messages.success(request, 'Resume deleted successfully')
        
    return redirect('accounts:dashboard')