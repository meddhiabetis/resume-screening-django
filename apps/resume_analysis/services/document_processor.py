import logging
import uuid
from typing import Dict, Any
from .neo4j_service import Neo4jService
from .pinecone_service import PineconeService
from .text_extractor import TextExtractor

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Processes resumes by extracting text and storing data in vector and graph databases.

    Attributes:
        text_extractor (TextExtractor): Instance of TextExtractor for extracting text from resumes.
        pinecone_service (PineconeService): Instance of PineconeService for storing vector embeddings.
        neo4j_service (Neo4jService): Instance of Neo4jService for storing resume data in a graph database.
    """

    def __init__(self):
        """Initializes the DocumentProcessor with necessary services."""
        self.text_extractor = TextExtractor()
        self.pinecone_service = PineconeService()
        self.neo4j_service = Neo4jService()

    def process_resume(self, file_path: str, user_id: str, original_filename: str) -> Dict[str, Any]:
        """Processes a resume file and stores the extracted data in both vector and graph databases.

        Args:
            file_path (str): The path to the resume file.
            user_id (str): The ID of the user submitting the resume.
            original_filename (str): The original filename of the resume.

        Returns:
            Dict[str, Any]: A dictionary containing the resume ID, vector ID, and extracted data.

        Raises:
            Exception: If an error occurs during the processing of the resume.
        """
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
        """Categorizes a skill into predefined categories.

        Args:
            skill (str): The skill to categorize.

        Returns:
            str: The category of the skill.
        """
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