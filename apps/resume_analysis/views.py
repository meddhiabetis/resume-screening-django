from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import default_storage
from django.conf import settings
from django.urls import reverse
import os
from .services.neo4j_service import Neo4jService
from .models import Resume, ResumeContent
from .services.document_processor import DocumentProcessor
from .services.text_extractor import TextExtractor
from .services.ocr_processor import OCRProcessor
import logging
from .services.pinecone_service import PineconeService
from django.views.decorators.http import require_http_methods
from .services.search_service import SearchService
from .services.hybrid_rag_service import HybridRAGService
import datetime 

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
                structured_data={},
                upload_date=datetime.datetime.utcnow(),
                uploaded_by=resume.user.username
            )

            # Extract features with retries
            logger.info(f"Processing resume {resume.file_id} for hybrid search")
            try:
                # Extract features
                extracted_data = content.extract_features()

                if "error" in extracted_data:
                    logger.warning(f"Partial feature extraction for {resume.file_id}: {extracted_data['error']}")
                    # Continue with partial processing
                    basic_features = {
                        'skills': {'technical': [], 'soft': []},
                        'work_experience': [],
                        'education': []
                    }
                    extracted_data = basic_features

                # Create vectors for Pinecone
                try:
                    pinecone_service = PineconeService()
                    vector_id = pinecone_service.create_vectors_for_resume(
                        resume_id=str(resume.file_id)
                    )
                    logger.info(f"Vectors created successfully for resume: {resume.file_id}")
                except Exception as vector_error:
                    logger.error(f"Error creating vectors: {str(vector_error)}")
                    vector_id = None

                # Add to Neo4j graph database
                try:
                    neo4j_service = Neo4jService()
                    
                    # Process skills
                    skills = []
                    if extracted_data.get('skills'):
                        # Process technical skills
                        for skill in extracted_data['skills'].get('technical', []):
                            if skill and isinstance(skill, str):
                                skills.append({
                                    'name': skill.lower().strip(),
                                    'category': 'technical',
                                    'confidence': 1.0
                                })
                        
                        # Process soft skills
                        for skill in extracted_data['skills'].get('soft', []):
                            if skill and isinstance(skill, str):
                                skills.append({
                                    'name': skill.lower().strip(),
                                    'category': 'soft',
                                    'confidence': 1.0
                                })

                    # Prepare resume data
                    resume_data = {
                        'id': str(resume.file_id),
                        'file_name': resume.original_filename,
                        'vector_id': vector_id,
                        'user_id': str(resume.user.id),
                        'metadata': {
                            'file_path': saved_path,
                            'processed_date': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                            'status': resume.status,
                            'uploaded_by': resume.user.username
                        },
                        'skills': skills
                    }

                    # Create or update in Neo4j
                    neo4j_service.create_or_update_resume(resume_data)
                    logger.info(f"Resume added to graph database: {resume.file_id}")

                except Exception as graph_error:
                    logger.error(f"Error adding to graph database: {str(graph_error)}")
                    # Continue processing even if graph storage fails

                # Update resume status
                if vector_id or skills:
                    resume.status = 'processed'
                else:
                    resume.status = 'partial'
                resume.save()

                return content

            except Exception as feature_error:
                logger.error(f"Error extracting features: {str(feature_error)}")
                resume.status = 'failed'
                resume.save()
                return None

        except Exception as processing_error:
            logger.error(f"Error processing file {file_obj.name}: {str(processing_error)}")
            resume.status = 'failed'
            resume.save()
            
            content = ResumeContent.objects.create(
                resume=resume,
                raw_text="Error processing document. Please ensure the file contains readable text.",
                structured_data={'error': str(processing_error)},
                upload_date=datetime.datetime.utcnow(),
                uploaded_by=resume.user.username
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
            
            # Delete from Neo4j
            try:
                from .services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                neo4j_service.delete_resume(str(resume.file_id))
            except Exception as graph_error:
                logger.error(f"Error deleting from Neo4j: {str(graph_error)}")
            
            # Delete file from storage
            file_path = os.path.join('resumes', str(resume.file_id), resume.original_filename)
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            
            # Delete database record
            resume.delete()
            messages.success(request, 'Resume deleted successfully from all systems')
            
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
def search_similar_resumes(request):
    """Search resumes using hybrid approach"""
    try:
        query = request.GET.get('query', '')
        search_type = request.GET.get('search_type', 'hybrid')
        
        if not query:
            return render(request, 'resume_analysis/search_results.html', {
                'results': [],
                'query': '',
                'search_type': search_type
            })

        results = []
        pinecone_service = PineconeService()
        neo4j_service = Neo4jService()

        if search_type in ['vector', 'hybrid']:
            # Get vector search results
            vector_results = pinecone_service.search_similar_resumes(
                query=query,
                section_type='full_text',
                limit=10
            )

            # Process vector results
            for match in vector_results:
                try:
                    resume_id = match.metadata.get('resume_id')
                    resume = Resume.objects.get(file_id=resume_id)
                    
                    result = {
                        'resume_id': resume_id,
                        'file_name': resume.original_filename,
                        'vector_score': float(match.score),
                        'graph_score': 0.0,
                        'combined_score': float(match.score),
                        'matching_skills': [],
                        'search_type': 'vector'
                    }
                    results.append(result)
                except Resume.DoesNotExist:
                    continue

        if search_type in ['graph', 'hybrid'] and results:
            # Use the top vector result as seed for graph search
            seed_resume_id = results[0]['resume_id']
            logger.info(f"Using resume {seed_resume_id} as seed for graph search")
            
            graph_results = neo4j_service.find_similar_resumes(
                resume_id=seed_resume_id,
                min_skill_match=2,
                limit=10
            )

            if search_type == 'graph':
                results = []  # Clear vector results if only graph search is requested

            # Process graph results
            for graph_result in graph_results:
                resume_id = graph_result['resume_id']
                try:
                    resume = Resume.objects.get(file_id=resume_id)
                    
                    # Check if this resume is already in results
                    existing_result = next(
                        (r for r in results if r['resume_id'] == resume_id),
                        None
                    )

                    if existing_result:
                        # Update existing result with graph information
                        existing_result['graph_score'] = float(graph_result['similarity_score'])
                        existing_result['matching_skills'] = graph_result.get('shared_skills', [])
                        if search_type == 'hybrid':
                            # Both scores are now normalized between 0 and 1
                            vector_weight = 0.6
                            graph_weight = 0.4
                            existing_result['combined_score'] = (
                                existing_result['vector_score'] * vector_weight +
                                existing_result['graph_score'] * graph_weight
                            )
                    else:
                        # Add new graph result
                        results.append({
                            'resume_id': resume_id,
                            'file_name': resume.original_filename,
                            'vector_score': 0.0,
                            'graph_score': float(graph_result['similarity_score']),
                            'combined_score': float(graph_result['similarity_score']) * 0.4,  # Apply graph weight
                            'matching_skills': graph_result.get('shared_skills', []),
                            'search_type': 'graph'
                        })
                except Resume.DoesNotExist:
                    continue

        # Sort results
        if search_type == 'hybrid':
            results.sort(key=lambda x: x['combined_score'], reverse=True)
        elif search_type == 'vector':
            results.sort(key=lambda x: x['vector_score'], reverse=True)
        else:  # graph
            results.sort(key=lambda x: x['graph_score'], reverse=True)

        # Add debug information
        for result in results:
            result['debug_info'] = {
                'search_type': search_type,
                'vector_score': f"{result['vector_score']:.3f}",
                'graph_score': f"{result['graph_score']:.3f}",
                'combined_score': f"{result['combined_score']:.3f}",
                'num_matching_skills': len(result.get('matching_skills', []))
            }

        logger.info(f"Search type: {search_type}")
        logger.info(f"Number of results: {len(results)}")
        logger.info(f"Top result scores: {[r['debug_info'] for r in results[:3]]}")

        return render(request, 'resume_analysis/search_results.html', {
            'results': results,
            'query': query,
            'search_type': search_type,
            'debug': True  # Add this to show debug information in template
        })

    except Exception as e:
        logger.error(f"Error in search_similar_resumes: {str(e)}")
        messages.error(request, f"Search error: {str(e)}")
        return redirect('accounts:dashboard')
    
def dashboard(request):
    resumes = Resume.objects.all()
    search_results = request.GET.get('search_results', None)

    return render(request, 'accounts/dashboard.html', {
        'resumes': resumes,
        'search_results': search_results
    })