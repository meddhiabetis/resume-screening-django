import datetime
import logging
import os
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from .models import Resume, ResumeContent
from .services.document_processor import DocumentProcessor
from .services.hybrid_rag_service import HybridRAGService
from .services.neo4j_service import Neo4jService
from .services.ocr_processor import OCRProcessor
from .services.pinecone_service import PineconeService
from .services.search_service import SearchService
from .services.text_extractor import TextExtractor

import logging
import re
from django.shortcuts import render
from apps.resume_analysis.models import Resume
from apps.resume_analysis.services.pinecone_service import PineconeService
from apps.resume_analysis.services.llm_query_service import MistralLLMQueryService

logger = logging.getLogger(__name__)

TITLE_VOCAB = [
    "data scientist","machine learning engineer","ml engineer","software engineer",
    "backend engineer","frontend engineer","data analyst","devops engineer",
    "data engineer","full stack developer","fullstack developer","research scientist",
    "ai engineer","ml researcher","ml scientist","product manager"
]

def _fallback_extract_entities(query: str):
    """Extract required skills, titles, companies, schools from the query (simple heuristics)."""
    q = (query or "")
    q_lower = q.lower()

    tokens = re.findall(r"[a-z0-9\+\#\.\-]+", q_lower)
    req_skills = list({t for t in tokens if len(t) >= 2})

    req_titles = [t for t in TITLE_VOCAB if t in q_lower]

    companies = set()
    for m in re.finditer(r"(?:worked|work|experience)\s+(?:at|with|for)\s+([a-zA-Z0-9\-\&\.\s]{2,})", q, flags=re.IGNORECASE):
        org = m.group(1).strip().lower()
        if org:
            companies.add(org)
            companies.add(org.split()[0])

    schools = set()
    for m in re.finditer(r"(?:studied|graduated)\s+(?:at|from)\s+([a-zA-Z0-9\-\&\.\s]{2,})", q, flags=re.IGNORECASE):
        sch = m.group(1).strip().lower()
        if sch:
            schools.add(sch)
            schools.add(sch.split()[0])

    org_words = {w for org in list(companies) + list(schools) for w in org.split()}
    req_skills = [t for t in req_skills if t not in org_words]

    return req_skills, req_titles, list(companies), list(schools)

def _build_explanation(row) -> str:
    """No-LLM explanation of how the graph score was computed."""
    parts = []
    if row.get('skills_total', 0) > 0:
        parts.append(f"skills {row.get('skills_hit', 0)}/{row.get('skills_total', 0)} (w={row.get('w_skills_norm', 0.0):.2f}, strength={row.get('skill_strength', 1.0):.2f})")
    if row.get('companies_total', 0) > 0:
        parts.append(f"companies {row.get('companies_hit', 0)}/{row.get('companies_total', 0)} (w={row.get('w_companies_norm', 0.0):.2f})")
    if row.get('schools_total', 0) > 0:
        parts.append(f"schools {row.get('schools_hit', 0)}/{row.get('schools_total', 0)} (w={row.get('w_schools_norm', 0.0):.2f})")
    if row.get('titles_total', 0) > 0:
        parts.append(f"titles {row.get('titles_hit', 0)}/{row.get('titles_total', 0)} (w={row.get('w_titles_norm', 0.0):.2f})")
    if not parts:
        return "no specific requirements detected in the query"
    return "; ".join(parts) + f". final graph {row.get('similarity_score', 0.0):.3f}"

def _get_float(request, name: str, default: float) -> float:
    val = request.GET.get(name)
    if val is None:
        return default
    try:
        f = float(val)
        if f < 0:
            return default
        return f
    except Exception:
        return default

def search_similar_resumes(request):
    """Search resumes: Vector, Graph (weighted, softened), or Hybrid (fused)."""
    try:
        query = request.GET.get('query', '')
        search_type = request.GET.get('search_type', 'hybrid')

        if not query:
            return render(request, 'resume_analysis/search_results.html', {
                'results': [], 'query': '', 'search_type': search_type
            })

        results = []
        pinecone = PineconeService()
        llm = MistralLLMQueryService()
        logger.info(f"LLM enabled: {llm.enabled}")

        # Vector search
        if search_type in ['vector', 'hybrid']:
            vector_results = pinecone.search_similar_resumes(query=query, section_type='full_text', limit=10)
            for match in vector_results:
                try:
                    resume_id = match.metadata.get('resume_id')
                    resume = Resume.objects.get(file_id=resume_id)
                    results.append({
                        'resume_id': resume_id,
                        'file_name': resume.original_filename,
                        'vector_score': float(match.score),
                        'graph_score': 0.0,
                        'combined_score': float(match.score),
                        'matching_skills': [],
                        'matched_titles': [],
                        'matched_companies': [],
                        'matched_schools': [],
                        'score_breakdown': None,
                        'score_explanation': None,
                        'search_type': 'vector'
                    })
                except Resume.DoesNotExist:
                    continue

        # Graph search (weighted across requested categories)
        graph_results = []
        if search_type in ['graph', 'hybrid']:
            # Entities (LLM for extraction; fallback if empty)
            plan = {"skills": [], "titles": [], "companies": [], "schools": []}
            if llm.enabled:
                p = llm.enhance_query(query, limit=10)
                plan.update({
                    "skills": p.get("skills", []),
                    "titles": p.get("titles", []),
                    "companies": p.get("companies", []) or p.get("orgs", []),
                    "schools": p.get("schools", []),
                })
            if not any([plan["skills"], plan["titles"], plan["companies"], plan["schools"]]):
                req_skills, req_titles, req_companies, req_schools = _fallback_extract_entities(query)
            else:
                req_skills = plan["skills"]
                req_titles = plan["titles"]
                req_companies = plan["companies"]
                req_schools = plan["schools"]

            # Read base weights from UI (default = equal 1/n → use 1.0 each; normalized in Cypher)
            base_w_skills = _get_float(request, 'w_skills', 1.0)
            base_w_companies = _get_float(request, 'w_companies', 1.0)
            base_w_schools = _get_float(request, 'w_schools', 1.0)
            base_w_titles = _get_float(request, 'w_titles', 1.0)

            cypher = llm.build_readonly_cypher_v3()
            rows = llm.run_builder_cypher(
                cypher=cypher,
                params={
                    "req_skills": req_skills,
                    "req_titles": req_titles,
                    "req_companies": req_companies,
                    "req_schools": req_schools,
                    "w_skills": base_w_skills,
                    "w_titles": base_w_titles,
                    "w_companies": base_w_companies,
                    "w_schools": base_w_schools,
                },
                limit=10
            )
            logger.info(f"Graph search (weighted) returned {len(rows)} rows")

            # Map graph rows
            for r in rows:
                graph_results.append({
                    "resume_id": r["resume_id"],
                    "file_name": r.get("file_name", ""),
                    "similarity_score": float(r.get("similarity_score", 0.0)),
                    "shared_skills": r.get("shared_skills", []),
                    "matched_titles": r.get("matched_titles", []),
                    "matched_companies": r.get("matched_companies", []),
                    "matched_schools": r.get("matched_schools", []),
                    "skills_hit": r.get("skills_hit", 0),
                    "skills_total": r.get("skills_total", 0),
                    "titles_hit": r.get("titles_hit", 0),
                    "titles_total": r.get("titles_total", 0),
                    "companies_hit": r.get("companies_hit", 0),
                    "companies_total": r.get("companies_total", 0),
                    "schools_hit": r.get("schools_hit", 0),
                    "schools_total": r.get("schools_total", 0),
                    "skill_strength": r.get("skill_strength", 1.0),
                    "w_skills_norm": r.get("w_skills_norm", 0.0),
                    "w_titles_norm": r.get("w_titles_norm", 0.0),
                    "w_companies_norm": r.get("w_companies_norm", 0.0),
                    "w_schools_norm": r.get("w_schools_norm", 0.0),
                })

            if search_type == 'graph':
                results = []  # graph only

            # Merge
            for gr in graph_results:
                resume_id = gr['resume_id']
                try:
                    resume = Resume.objects.get(file_id=resume_id)
                except Resume.DoesNotExist:
                    continue

                explanation = _build_explanation({
                    **gr,
                    "similarity_score": gr.get("similarity_score", 0.0)
                })

                existing = next((r for r in results if r['resume_id'] == resume_id), None)
                if existing:
                    existing['graph_score'] = float(gr.get('similarity_score', 0.0))
                    existing['matching_skills'] = gr.get('shared_skills', [])
                    existing['matched_titles'] = gr.get('matched_titles', [])
                    existing['matched_companies'] = gr.get('matched_companies', [])
                    existing['matched_schools'] = gr.get('matched_schools', [])
                    existing['score_breakdown'] = {
                        'skills_hit': gr.get('skills_hit', 0),
                        'skills_total': gr.get('skills_total', 0),
                        'titles_hit': gr.get('titles_hit', 0),
                        'titles_total': gr.get('titles_total', 0),
                        'companies_hit': gr.get('companies_hit', 0),
                        'companies_total': gr.get('companies_total', 0),
                        'schools_hit': gr.get('schools_hit', 0),
                        'schools_total': gr.get('schools_total', 0),
                        'skill_strength': gr.get('skill_strength', 1.0),
                        'w_skills_norm': gr.get('w_skills_norm', 0.0),
                        'w_titles_norm': gr.get('w_titles_norm', 0.0),
                        'w_companies_norm': gr.get('w_companies_norm', 0.0),
                        'w_schools_norm': gr.get('w_schools_norm', 0.0),
                        'final_graph': float(gr.get('similarity_score', 0.0)),
                    }
                    existing['score_explanation'] = explanation
                    if search_type == 'hybrid':
                        existing['combined_score'] = existing['vector_score']*0.6 + existing['graph_score']*0.4
                        existing['search_type'] = 'hybrid'
                else:
                    graph_score = float(gr.get('similarity_score', 0.0))
                    results.append({
                        'resume_id': resume_id,
                        'file_name': resume.original_filename,
                        'vector_score': 0.0,
                        'graph_score': graph_score,
                        'combined_score': graph_score * (0.4 if search_type == 'hybrid' else 1.0),
                        'matching_skills': gr.get('shared_skills', []),
                        'matched_titles': gr.get('matched_titles', []),
                        'matched_companies': gr.get('matched_companies', []),
                        'matched_schools': gr.get('matched_schools', []),
                        'score_breakdown': {
                            'skills_hit': gr.get('skills_hit', 0),
                            'skills_total': gr.get('skills_total', 0),
                            'titles_hit': gr.get('titles_hit', 0),
                            'titles_total': gr.get('titles_total', 0),
                            'companies_hit': gr.get('companies_hit', 0),
                            'companies_total': gr.get('companies_total', 0),
                            'schools_hit': gr.get('schools_hit', 0),
                            'schools_total': gr.get('schools_total', 0),
                            'skill_strength': gr.get('skill_strength', 1.0),
                            'w_skills_norm': gr.get('w_skills_norm', 0.0),
                            'w_titles_norm': gr.get('w_titles_norm', 0.0),
                            'w_companies_norm': gr.get('w_companies_norm', 0.0),
                            'w_schools_norm': gr.get('w_schools_norm', 0.0),
                            'final_graph': graph_score,
                        },
                        'score_explanation': explanation,
                        'search_type': 'graph' if search_type == 'graph' else 'hybrid'
                    })

        # Sort and render
        if search_type == 'hybrid':
            results.sort(key=lambda x: x['combined_score'], reverse=True)
        elif search_type == 'vector':
            results.sort(key=lambda x: x['vector_score'], reverse=True)
        else:
            results.sort(key=lambda x: x['graph_score'], reverse=True)

        return render(request, 'resume_analysis/search_results.html', {
            'results': results, 'query': query, 'search_type': search_type
        })
    except Exception as e:
        logger.exception(f"Search failed: {e}")
        return render(request, 'resume_analysis/search_results.html', {
            'results': [], 'query': request.GET.get('query', ''), 'search_type': request.GET.get('search_type', 'hybrid')
        })

def process_resume(file_obj, resume):
    """Process the uploaded resume file.

    Args:
        file_obj: The uploaded file object.
        resume: The Resume instance associated with the uploaded file.

    Returns:
        ResumeContent instance if processing is successful, None otherwise.
    """
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
    """Render the upload form for resumes."""
    return render(request, 'resume_analysis/upload_form.html')

@login_required
def upload_resumes(request):
    """Handle the upload of resumes.

    Args:
        request: The HTTP request object.

    Returns:
        JsonResponse indicating success or failure of the upload.
    """
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
    """View a specific resume and its content.

    Args:
        request: The HTTP request object.
        file_id: The ID of the resume to view.

    Returns:
        Rendered HTML response with resume details.
    """
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
    """Delete a specific resume and its associated data.

    Args:
        request: The HTTP request object.
        file_id: The ID of the resume to delete.

    Returns:
        Redirects to the dashboard after deletion.
    """
    if request.method == 'POST':
        resume = get_object_or_404(Resume, file_id=file_id, user=request.user)
        
        try:
            # Delete vectors from Pinecone
            pinecone_service = PineconeService()
            pinecone_service.delete_resume_vectors(str(resume.file_id))
            
            # Delete from Neo4j
            try:
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
    """Extract features from a processed resume.

    Args:
        request: The HTTP request object.
        file_id: The ID of the resume from which to extract features.

    Returns:
        JsonResponse with extracted features or error details.
    """
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

  
def dashboard(request):
    """Render the dashboard showing all resumes.

    Args:
        request: The HTTP request object.

    Returns:
        Rendered HTML response with the dashboard view.
    """
    resumes = Resume.objects.all()
    search_results = request.GET.get('search_results', None)

    return render(request, 'accounts/dashboard.html', {
        'resumes': resumes,
        'search_results': search_results
    })