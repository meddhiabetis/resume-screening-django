import logging
from typing import List, Dict, Any
from ..models import Resume
from .neo4j_service import Neo4jService
from .pinecone_service import PineconeService

logger = logging.getLogger(__name__)

class HybridRAGService:
    """
    Service for performing hybrid resume analysis using vector and graph-based approaches.
    Attributes:
        neo4j (Neo4jService)
        pinecone (PineconeService)
    """

    def __init__(self):
        """Initialize the HybridRAGService with Neo4j and Pinecone services."""
        self.neo4j = Neo4jService()
        self.pinecone = PineconeService()

    def search_resumes(self, 
                      query: str,
                      vector_weight: float = 0.6,
                      graph_weight: float = 0.4,
                      limit: int = 10) -> List[Dict[str, Any]]:
        """
        Existing hybrid search; unchanged here.
        Kept for compatibility with any callers using this service directly.
        """
        try:
            vector_results = self.pinecone.search_similar_resumes(
                query=query,
                section_type='full_text',
                limit=limit
            )
            vector_results_processed = []
            for match in vector_results:
                resume_id = match.metadata.get('resume_id')
                try:
                    resume = Resume.objects.get(file_id=resume_id)
                    vector_results_processed.append({
                        'resume_id': resume_id,
                        'file_name': resume.original_filename,
                        'score': float(match.score),
                        'metadata': {
                            'content': match.metadata.get('content', ''),
                            'section_type': match.metadata.get('section_type', '')
                        }
                    })
                except Resume.DoesNotExist:
                    logger.warning(f"Resume {resume_id} not found in database")
                    continue

            # Optionally call independent graph search here as well (not mandatory in this service)
            # combined_results = self._merge_results(...)

            return vector_results_processed[:limit]
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            raise

    def _merge_results(self,
                      vector_results: List[Dict],
                      graph_results: List[Dict],
                      vector_weight: float,
                      graph_weight: float,
                      limit: int) -> List[Dict]:
        """Existing merging logic; not central to the current step."""
        merged = {}
        for result in vector_results:
            resume_id = result['resume_id']
            if resume_id not in merged:
                merged[resume_id] = {
                    'resume_id': resume_id,
                    'file_name': result['file_name'],
                    'vector_score': result['score'] * vector_weight,
                    'graph_score': 0,
                    'combined_score': 0,
                    'metadata': result['metadata'],
                    'matching_skills': set(),
                    'experiences': []
                }
        for result in graph_results:
            resume_id = result['resume_id']
            if resume_id not in merged:
                merged[resume_id] = {
                    'resume_id': resume_id,
                    'file_name': result['file_name'],
                    'vector_score': 0,
                    'graph_score': 0,
                    'combined_score': 0,
                    'metadata': {},
                    'matching_skills': set(result.get('shared_skills', [])),
                    'experiences': result.get('experiences', [])
                }
            graph_score = (result.get('similarity_score', 0) * graph_weight)
            merged[resume_id]['graph_score'] = max(merged[resume_id]['graph_score'], graph_score)
            if 'shared_skills' in result:
                merged[resume_id]['matching_skills'].update(result['shared_skills'])
            if 'experiences' in result:
                merged[resume_id]['experiences'] = result['experiences']
        for item in merged.values():
            item['combined_score'] = item['vector_score'] + item['graph_score']
            item['matching_skills'] = list(item['matching_skills'])
        sorted_results = sorted(merged.values(), key=lambda x: x['combined_score'], reverse=True)
        return sorted_results[:limit]

    def add_resume_to_graph(self, 
                            resume_id: str,
                            file_name: str,
                            user_id: str,
                            extracted_data: Dict[str, Any]) -> None:
        """
        Enrich graph with skills, titles, companies, and schools for a resume.
        extracted_data is expected to contain:
          - skills: {'technical': [...], 'soft': [...]}
          - experiences or experience: List[Dict{company/org/employer, title/role, start_year, end_year}]
          - education: List[Dict{school/university/institution, degree}]
        """
        try:
            # Build skill list
            skills = []
            if 'skills' in extracted_data:
                technical_skills = extracted_data['skills'].get('technical', []) or []
                soft_skills = extracted_data['skills'].get('soft', []) or []
                for skill in technical_skills:
                    skills.append({'name': str(skill), 'category': 'technical', 'confidence': 1.0})
                for skill in soft_skills:
                    skills.append({'name': str(skill), 'category': 'soft', 'confidence': 1.0})

            # Titles from experiences; experiences with company + role
            experiences_src = extracted_data.get('experiences') or extracted_data.get('experience') or []
            titles = []
            experiences = []
            for exp in experiences_src:
                company = exp.get('company') or exp.get('organization') or exp.get('employer')
                role = exp.get('title') or exp.get('role')
                start_year = exp.get('start_year') or exp.get('start') or exp.get('from')
                end_year = exp.get('end_year') or exp.get('end') or exp.get('to')
                if role:
                    titles.append(str(role))
                experiences.append({
                    'company': company or '',
                    'role': role or '',
                    'start_year': start_year,
                    'end_year': end_year
                })

            # Education
            education_src = extracted_data.get('education') or []
            education = []
            for ed in education_src:
                school = ed.get('school') or ed.get('university') or ed.get('institution')
                degree = ed.get('degree') or ''
                education.append({'school': school or '', 'degree': degree or ''})

            resume_graph_payload = {
                'id': resume_id,
                'file_name': file_name,
                'user_id': user_id,
                'skills': skills,
                'titles': list({t for t in titles if t}),
                'experiences': [e for e in experiences if e.get('company')],
                'education': [e for e in education if e.get('school')],
            }

            self.neo4j.create_or_update_resume(resume_graph_payload)
            logger.info(f"Resume added/updated in graph database: {resume_id}")

        except Exception as e:
            logger.warning(f"Failed to add resume {resume_id} to graph: {e}")