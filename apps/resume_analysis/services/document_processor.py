from .text_extractor import TextExtractor
from .pinecone_service import PineconeService
from .neo4j_service import Neo4jService
import logging
from typing import Dict, Any
import uuid

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.pinecone_service = PineconeService()
        self.neo4j_service = Neo4jService()

    def process_resume(self, file_path: str, user_id: str, original_filename: str) -> Dict[str, Any]:
        """Process a resume and store in both vector and graph databases"""
        try:
            # Extract text and structured data
            extracted_data = self.text_extractor.extract(file_path)
            
            # Generate unique ID for the resume
            resume_id = str(uuid.uuid4())
            
            # Create vector embedding and store in Pinecone
            vector_id = self.pinecone_service.store_resume(
                text=extracted_data['full_text'],
                metadata={
                    'resume_id': resume_id,
                    'file_name': original_filename,
                    'user_id': user_id,
                    'skills': extracted_data.get('skills', []),
                    'companies': [exp['company'] for exp in extracted_data.get('experiences', [])]
                }
            )

            # Store in Neo4j
            resume_data = {
                'id': resume_id,
                'file_name': original_filename,
                'vector_id': vector_id,
                'user_id': user_id,
                'metadata': {
                    'file_path': file_path,
                    'processed_date': extracted_data.get('processed_date'),
                    'language': extracted_data.get('language'),
                },
                'skills': [
                    {
                        'name': skill,
                        'category': self._categorize_skill(skill),
                        'confidence': 1.0  # You can implement confidence scoring
                    }
                    for skill in extracted_data.get('skills', [])
                ],
                'experiences': extracted_data.get('experiences', []),
                'education': extracted_data.get('education', [])
            }

            self.neo4j_service.create_or_update_resume(resume_data)

            return {
                'resume_id': resume_id,
                'vector_id': vector_id,
                'extracted_data': extracted_data
            }

        except Exception as e:
            logger.error(f"Error processing resume: {str(e)}")
            raise

    def _categorize_skill(self, skill: str) -> str:
        """Categorize skills into predefined categories"""
        # Implement your skill categorization logic here
        # This is a simple example - you should expand this
        skill = skill.lower()
        categories = {
            'programming': ['python', 'java', 'javascript', 'c++', 'ruby'],
            'database': ['sql', 'mongodb', 'postgresql', 'mysql', 'neo4j'],
            'framework': ['django', 'flask', 'react', 'angular', 'vue'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes'],
            'tools': ['git', 'jenkins', 'jira', 'confluence', 'bitbucket']
        }

        for category, skills in categories.items():
            if skill in skills:
                return category
        return 'other'