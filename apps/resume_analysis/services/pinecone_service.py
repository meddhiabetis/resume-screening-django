import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from django.conf import settings
from ..models import Resume
import logging

logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        self.api_key = settings.PINECONE_API_KEY
        self.environment = settings.PINECONE_ENVIRONMENT
        self.index_name = settings.PINECONE_INDEX
        logger.info(f"Initializing PineconeService with index: {self.index_name}")
        
        # Use the locally downloaded model
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        
        # Initialize Pinecone and connect to existing index
        self.pc = Pinecone(api_key=self.api_key)
        
        # Just connect to the index - don't try to create or delete
        self.index = self.pc.Index(self.index_name)
        logger.info(f"Connected to existing Pinecone index: {self.index_name}")
    def create_vectors_for_resume(self, resume_id: str) -> str:
        """Create vectors for all sections of a resume"""
        try:
            logger.info(f"Starting vector creation for resume: {resume_id}")
            resume = Resume.objects.get(file_id=resume_id)
            content = resume.resumecontent
            features = content.extracted_features or {}  # Default to empty dict if None

            # Create full text vector
            logger.info(f"Creating full text vector for resume: {resume_id}")
            skills = []
            if features.get('skills'):
                skills = (
                    features['skills'].get('technical', []) +
                    features['skills'].get('soft', [])
                )

            self._create_vector_for_section(
                resume=resume,
                section_type='full_text',
                content=content.raw_text,
                metadata={
                    'resume_id': str(resume.file_id),
                    'file_name': resume.original_filename,
                    'section_type': 'full_text',
                    'skills': skills
                }
            )

            # Only create skills vector if we have skills data
            if features.get('skills'):
                logger.info(f"Creating skills vector for resume: {resume_id}")
                skills_text = ' '.join([
                    ' '.join(features['skills'].get('technical', [])),
                    ' '.join(features['skills'].get('soft', []))
                ]).strip()
                
                if skills_text:  # Only create skills vector if we have skills text
                    self._create_vector_for_section(
                        resume=resume,
                        section_type='skills',
                        content=skills_text,
                        metadata={
                            'resume_id': str(resume.file_id),
                            'file_name': resume.original_filename,
                            'section_type': 'skills',
                            'skills': skills
                        }
                    )

            return f"{resume_id}-full_text"  # Return the main vector ID

        except Exception as e:
            logger.error(f"Error creating vectors for resume {resume_id}: {str(e)}")
            raise

    def _create_vector_for_section(self, resume: Resume, section_type: str, content: str, metadata: dict = None) -> None:
        """Create a vector for a specific section of a resume"""
        try:
            logger.info(f"Creating vector for section {section_type} of resume {resume.file_id}")
            embedding = self.model.encode(content).tolist()
            
            # Prepare metadata
            base_metadata = {
                'resume_id': str(resume.file_id),
                'section_type': section_type,
                'content': content[:1000]  # Limit content length in metadata
            }
            
            # Update with additional metadata if provided
            if metadata:
                base_metadata.update(metadata)
            
            vector_id = f"{resume.file_id}-{section_type}"
            logger.info(f"Upserting vector with ID: {vector_id}")
            self.index.upsert([(vector_id, embedding, base_metadata)])
            logger.info(f"Successfully created vector for section {section_type} of resume {resume.file_id}")
        except Exception as e:
            logger.error(f"Error in _create_vector_for_section: {str(e)}")
            raise

    def search_similar_resumes(self, query: str, section_type: str = 'full_text', limit: int = 10) -> list:
        """Search for similar resumes using Pinecone"""
        try:
            logger.info(f"Searching resumes with query: '{query}', section_type: {section_type}")
            query_embedding = self.model.encode(query).tolist()
            logger.info("Created query embedding, searching Pinecone...")
            
            # Add filter only if section_type is specified and not 'all'
            filter_dict = {"section_type": section_type} if section_type not in ('all', '') else None
            
            results = self.index.query(
                vector=query_embedding,
                top_k=limit,
                include_metadata=True,
                filter=filter_dict
            )
            
            logger.info(f"Search complete. Found {len(results['matches'])} matches")
            for match in results['matches']:
                logger.info(f"Match score: {match.score}, Resume ID: {match.metadata.get('resume_id')}")
            
            return results['matches']

        except Exception as e:
            logger.error(f"Error searching similar resumes: {str(e)}")
            raise
        

    def delete_resume_vectors(self, resume_id: str) -> bool:
        """Delete all vectors associated with a resume"""
        try:
            logger.info(f"Deleting vectors for resume: {resume_id}")
            vector_ids = [
                f"{resume_id}-full_text",
                f"{resume_id}-skills",
                f"{resume_id}-experience"
            ]
            self.index.delete(ids=vector_ids)
            logger.info(f"Successfully deleted vectors for resume: {resume_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting vectors for resume {resume_id}: {str(e)}")
            raise        