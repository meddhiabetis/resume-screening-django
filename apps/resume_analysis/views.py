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

@login_required
def upload_resume(request):
    if request.method == 'POST':
        if 'resume' not in request.FILES:
            messages.error(request, 'Please select a file to upload')
            return redirect('dashboard')

        file = request.FILES['resume']
        
        # Validate file size
        if file.size > settings.MAX_UPLOAD_SIZE:
            messages.error(request, f'File size exceeds {settings.MAX_UPLOAD_SIZE/1024/1024}MB limit')
            return redirect('dashboard')

        # Validate file type
        if file.content_type not in settings.ALLOWED_RESUME_TYPES:
            messages.error(request, 'Invalid file type. Please upload PDF or Word documents.')
            return redirect('dashboard')

        try:
            # Create resume record
            resume = Resume.objects.create(
                user=request.user,
                original_filename=file.name,
                status='processing'
            )

            # Save file and process
            file_path = os.path.join('resumes', str(resume.file_id), file.name)
            file_path = default_storage.save(file_path, file)

            # Process document
            doc_processor = DocumentProcessor()
            text_extractor = TextExtractor()
            
            extracted_text = text_extractor.extract(file, file.name)

            # Create resume content
            ResumeContent.objects.create(
                resume=resume,
                raw_text=extracted_text,
                structured_data={}
            )

            resume.status = 'processed'
            resume.save()
            
            messages.success(request, 'Resume uploaded and processed successfully')
            return redirect('dashboard')

        except Exception as e:
            if resume:
                resume.status = 'failed'
                resume.save()
            messages.error(request, f'Error processing resume: {str(e)}')
            return redirect('dashboard')

    return redirect('dashboard')

@login_required
def view_resume(request, file_id):
    resume = get_object_or_404(Resume, file_id=file_id, user=request.user)
    content = get_object_or_404(ResumeContent, resume=resume)
    
    context = {
        'resume': resume,
        'content': content,
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
        
    return redirect('dashboard')