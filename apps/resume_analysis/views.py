from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import default_storage
from django.conf import settings
from django.urls import reverse
import os
from .models import Resume, ResumeContent
from .services.document_processor import DocumentProcessor
from .services.text_extractor import TextExtractor
from .services.ocr_processor import OCRProcessor
import logging

logger = logging.getLogger(__name__)

def process_resume(file_obj, resume):
    """Process the uploaded resume file"""
    try:
        # Save file
        file_path = os.path.join('resumes', str(resume.file_id), file_obj.name)
        saved_path = default_storage.save(file_path, file_obj)
        full_file_path = os.path.join(settings.MEDIA_ROOT, saved_path)

        # Process document
        text_extractor = TextExtractor()
        
        try:
            extracted_text = text_extractor.extract(file_obj, file_obj.name)
            
            if not extracted_text or len(extracted_text.strip()) < 50:
                logger.warning(f"Insufficient text extracted from {file_obj.name}, attempting OCR")
                # Try OCR as fallback
                ocr_processor = OCRProcessor()
                extracted_text = ocr_processor.process_pdf_with_ocr(full_file_path)

            if not extracted_text or len(extracted_text.strip()) < 50:
                raise ValueError("Could not extract sufficient text from the document")

            # Create resume content
            content = ResumeContent.objects.create(
                resume=resume,
                raw_text=extracted_text,
                structured_data={}
            )

            resume.status = 'processed'
            resume.save()
            
            return content

        except Exception as processing_error:
            logger.error(f"Error processing file {file_obj.name}: {str(processing_error)}")
            resume.status = 'failed'
            resume.save()
            
            content = ResumeContent.objects.create(
                resume=resume,
                raw_text="Error processing document. Please ensure the file contains readable text.",
                structured_data={'error': str(processing_error)}
            )
            
            return None

    except Exception as e:
        logger.error(f"Error in process_resume: {str(e)}")
        if resume:
            resume.status = 'failed'
            resume.save()
        return None

@login_required
def upload_form(request):
    return render(request, 'resume_analysis/upload_form.html')

@login_required
def upload_resume(request):
    if request.method == 'POST':
        try:
            if 'resume' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a file to upload'
                })

            file = request.FILES['resume']
            
            # Validate file size
            if file.size > settings.MAX_UPLOAD_SIZE:
                return JsonResponse({
                    'success': False,
                    'error': f'File size exceeds {settings.MAX_UPLOAD_SIZE/1024/1024}MB limit'
                })

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
                return JsonResponse({
                    'success': False,
                    'error': 'Unsupported file type. Please upload PDF, Word documents, or images.'
                })

            # Create Resume instance
            resume = Resume.objects.create(
                user=request.user,
                original_filename=file.name,
                status='processing'
            )
            
            # Process the resume
            content = process_resume(file, resume)
            
            if content:
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('resume_analysis:view_resume', args=[resume.file_id])
                })
            else:
                resume.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to process resume.'
                })
                
        except Exception as e:
            logger.error(f"Error in upload_resume: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
def view_resume(request, file_id):
    resume = get_object_or_404(Resume, file_id=file_id, user=request.user)
    content = get_object_or_404(ResumeContent, resume=resume)
    
    context = {
        'resume': resume,
        'content': content,
        'error': content.structured_data.get('error', None) if resume.status == 'failed' else None,
        'features': content.extracted_features if content.extracted_features else None
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

@login_required
def extract_features(request, file_id):
    """Extract features from a processed resume"""
    resume = get_object_or_404(Resume, file_id=file_id, user=request.user)
    content = get_object_or_404(ResumeContent, resume=resume)
    
    if resume.status != 'processed':
        return JsonResponse({
            'error': 'Resume must be processed before extracting features'
        }, status=400)
    
    try:
        features = content.extract_features()
        if 'error' in features:
            return JsonResponse({
                'error': features['error'],
                'details': features.get('details', ''),
                'raw_response': features.get('raw_response', '')
            }, status=500)
        
        return JsonResponse({
            'success': True,
            'features': features
        })
    except Exception as e:
        return JsonResponse({
            'error': f'Feature extraction failed: {str(e)}',
            'details': getattr(content, 'processing_error', None)
        }, status=500)