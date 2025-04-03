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
from .services.pinecone_service import PineconeService
from django.views.decorators.http import require_http_methods
from .services.search_service import SearchService

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

            # Automatically extract features
            logger.info(f"Automatically extracting features for resume: {resume.file_id}")
            try:
                features = content.extract_features()
                logger.info(f"Features extracted successfully for resume: {resume.file_id}")
            except Exception as feature_error:
                logger.error(f"Error extracting features: {str(feature_error)}")
                # Continue even if feature extraction fails
                features = None

            resume.status = 'processed'
            resume.save()

            # Create vectors for search
            try:
                pinecone_service = PineconeService()
                pinecone_service.create_vectors_for_resume(str(resume.file_id))
                logger.info(f"Vectors created successfully for resume: {resume.file_id}")
            except Exception as vector_error:
                logger.error(f"Error creating vectors: {str(vector_error)}")
            
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
def upload_resumes(request):
    if request.method == 'POST':
        try:
            files = request.FILES.getlist('resumes')
            if not files:
                return JsonResponse({'success': False, 'error': 'No files provided'})

            successful_uploads = []
            failed_uploads = []

            for file in files:
                try:
                    # Create resume instance
                    resume = Resume.objects.create(
                        user=request.user,
                        original_filename=file.name,
                        status='processing'
                    )

                    # Process the resume
                    content = process_resume(file, resume)
                    
                    if content:
                        successful_uploads.append(file.name)
                    else:
                        failed_uploads.append(file.name)
                        
                except Exception as e:
                    logger.error(f"Error processing file {file.name}: {str(e)}")
                    failed_uploads.append(file.name)
                    continue

            response_data = {
                'success': True,
                'message': f'Successfully processed {len(successful_uploads)} files',
                'successful_uploads': successful_uploads,
                'failed_uploads': failed_uploads
            }

            if failed_uploads:
                response_data['warning'] = f'Failed to process {len(failed_uploads)} files'

            return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"Error in batch upload: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

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
        
        try:
            # Delete vectors from Pinecone
            pinecone_service = PineconeService()
            pinecone_service.delete_resume_vectors(str(resume.file_id))
            
            # Delete file from storage
            file_path = os.path.join('resumes', str(resume.file_id), resume.original_filename)
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            
            # Delete database record
            resume.delete()
            messages.success(request, 'Resume and associated vectors deleted successfully')
            
        except Exception as e:
            logger.error(f"Error deleting resume {file_id}: {str(e)}")
            messages.error(request, f'Error deleting resume: {str(e)}')
            
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
        
@require_http_methods(["GET", "POST"])
def search_similar_resumes(request):
    try:
        if request.method == "POST":
            query = request.POST.get('query')
            section_type = request.POST.get('section_type', 'full_text')
            limit = int(request.POST.get('limit', 10))
        else:
            query = request.GET.get('query')
            section_type = request.GET.get('section_type', 'full_text')
            limit = int(request.GET.get('limit', 10))

        logger.info(f"Received search request - Query: {query}, Section: {section_type}")

        if not query:
            return render(request, 'resume_analysis/search_results.html', {
                'results': [],
                'query': '',
                'section_type': section_type
            })

        search_service = SearchService()
        results = search_service.search_similar_resumes(query, section_type, limit)

        logger.info(f"Search completed - Found {len(results)} results")

        # Transform results for template rendering
        processed_results = []
        for match in results:
            metadata = match.metadata
            processed_results.append({
                'resume_id': metadata.get('resume_id'),
                'score': float(match.score),
                'content': metadata.get('content', '')[:500],
                'section_type': metadata.get('section_type')
            })

        return render(request, 'resume_analysis/search_results.html', {
            'results': processed_results,
            'query': query,
            'section_type': section_type
        })

    except Exception as e:
        logger.error(f"Error in search_similar_resumes: {str(e)}")
        return render(request, 'resume_analysis/search_results.html', {
            'error': str(e),
            'query': query if 'query' in locals() else '',
            'section_type': section_type if 'section_type' in locals() else 'full_text'
        })
        
def dashboard(request):
    resumes = Resume.objects.all()
    search_results = request.GET.get('search_results', None)

    return render(request, 'accounts/dashboard.html', {
        'resumes': resumes,
        'search_results': search_results
    })