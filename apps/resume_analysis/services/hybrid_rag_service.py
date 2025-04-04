from typing import List, Dict, Any
from .neo4j_service import Neo4jService
from .pinecone_service import PineconeService
import logging
from ..models import Resume

logger = logging.getLogger(__name__)

class HybridRAGService:
    def __init__(self):
        self.neo4j = Neo4jService()
        self.pinecone = PineconeService()

    def search_resumes(self, 
                      query: str,
                      vector_weight: float = 0.6,
                      graph_weight: float = 0.4,
                      limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search using both vector and graph-based approaches
        """
        try:
            # Get vector search results
            vector_results = self.pinecone.search_similar_resumes(
                query=query,
                section_type='full_text',  # Use full text for main search
                limit=limit
            )

            # Convert Pinecone results to our format
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

            # Get graph search results
            graph_results = []
            if vector_results_processed:  # Use first result as seed for graph search
                first_resume_id = vector_results_processed[0]['resume_id']
                similar_resumes = self.neo4j.find_similar_resumes(
                    resume_id=first_resume_id,
                    min_skill_match=2,
                    limit=limit
                )
                graph_results.extend(similar_resumes)

            # Combine and rank results
            combined_results = self._merge_results(
                vector_results=vector_results_processed,
                graph_results=graph_results,
                vector_weight=vector_weight,
                graph_weight=graph_weight,
                limit=limit
            )

            return combined_results

        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            raise

    def _merge_results(self,
                      vector_results: List[Dict],
                      graph_results: List[Dict],
                      vector_weight: float,
                      graph_weight: float,
                      limit: int) -> List[Dict]:
        """
        Merge and rank results from both vector and graph searches
        """
        merged = {}

        # Process vector results
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

        # Process graph results
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

            # Update graph score
            graph_score = (result.get('similarity_score', 0) * graph_weight)
            merged[resume_id]['graph_score'] = max(
                merged[resume_id]['graph_score'],
                graph_score
            )
            if 'shared_skills' in result:
                merged[resume_id]['matching_skills'].update(result['shared_skills'])
            if 'experiences' in result:
                merged[resume_id]['experiences'] = result['experiences']

        # Calculate combined scores
        for item in merged.values():
            item['combined_score'] = item['vector_score'] + item['graph_score']
            item['matching_skills'] = list(item['matching_skills'])

        # Sort by combined score and limit results
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )

        return sorted_results[:limit]

    def add_resume_to_graph(self, 
                          resume_id: str,
                          file_name: str,
                          user_id: str,
                          extracted_data: Dict[str, Any]):
        """Add a resume to the graph database"""
        try:
            # Process skills
            skills = []
            if 'skills' in extracted_data:
                technical_skills = extracted_data['skills'].get('technical', [])
                soft_skills = extracted_data['skills'].get('soft', [])
                
                for skill in technical_skills:
                    skills.append({
                        'name': skill,
                        'category': 'technical',
                        'confidence': 1.0
                    })
                
                for skill in soft_skills:
                    skills.append({
                        'name': skill,
                        'category': 'soft',
                        'confidence': 1.0
                    })

            # Process experiences
            experiences = []
            if 'work_experience' in extracted_data:
                for exp in extracted_data['work_experience']:
                    experiences.append({
                        'title': exp.get('title', ''),
                        'company': exp.get('company', ''),
                        'start_date': exp.get('start_date', ''),
                        'end_date': exp.get('end_date', ''),
                        'description': ' '.join(exp.get('responsibilities', []))
                    })

            # Process education
            education = []
            if 'education' in extracted_data:
                for edu in extracted_data['education']:
                    education.append({
                        'degree': edu.get('degree', ''),
                        'institution': edu.get('institution', ''),
                        'start_date': edu.get('start_date', ''),
                        'end_date': edu.get('end_date', '')
                    })

            resume_data = {
                'id': resume_id,
                'file_name': file_name,
                'vector_id': f"{resume_id}-full_text",  # Match your vector ID format
                'user_id': user_id,
                'metadata': {
                    'processed_date': extracted_data.get('processed_date'),
                    'language': extracted_data.get('language'),
                },
                'skills': skills,
                'experiences': experiences,
                'education': education
            }

            self.neo4j.create_or_update_resume(resume_data)
            logger.info(f"Resume {resume_id} added to graph database")

        except Exception as e:
            logger.error(f"Error adding resume to graph: {str(e)}")
            raise