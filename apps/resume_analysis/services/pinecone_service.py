import os
from pinecone import Pinecone, ServerlessSpec
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
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.api_key)

        # Check if index exists, otherwise create it
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=384,
                metric="cosine",  # Change metric if needed
                spec=ServerlessSpec(cloud="aws", region="us-west-2")  # Adjust region if needed
            )
        
        # Connect to the index
        self.index = self.pc.Index(self.index_name)
    
    def create_vectors_for_resume(self, resume_id: str) -> None:
        """Create vectors for all sections of a resume"""
        try:
            resume = Resume.objects.get(file_id=resume_id)
            content = resume.resumecontent
            features = content.extracted_features

            # Create full text vector
            self._create_vector_for_section(
                resume=resume,
                section_type='full_text',
                content=content.raw_text
            )

            if features:
                # Skills vector
                if 'skills' in features:
                    skills_text = ' '.join([
                        ' '.join(features['skills'].get('technical', [])),
                        ' '.join(features['skills'].get('soft', []))
                    ])
                    self._create_vector_for_section(
                        resume=resume,
                        section_type='skills',
                        content=skills_text
                    )

                # Experience vector
                if 'work_experience' in features:
                    experience_text = ' '.join([
                        f"{exp.get('company', '')} {exp.get('title', '')} {' '.join(exp.get('responsibilities', []))}"
                        for exp in features['work_experience']
                    ])
                    self._create_vector_for_section(
                        resume=resume,
                        section_type='experience',
                        content=experience_text
                    )

        except Exception as e:
            logger.error(f"Error creating vectors for resume {resume_id}: {str(e)}")
            raise

    def _create_vector_for_section(self, resume: Resume, section_type: str, content: str) -> None:
        embedding = self.model.encode(content).tolist()
        metadata = {
            'resume_id': resume.file_id,
            'section_type': section_type,
            'content': content
        }
        self.index.upsert([(f"{resume.file_id}-{section_type}", embedding, metadata)])

    def search_similar_resumes(self, query: str, section_type: str = 'full_text', limit: int = 10) -> list:
        """Search for similar resumes using Pinecone"""
        try:
            query_embedding = self.model.encode(query).tolist()
            results = self.index.query(vector=query_embedding, top_k=limit, include_metadata=True)  # FIXED HERE
            return results['matches']

        except Exception as e:
            logger.error(f"Error searching similar resumes: {str(e)}")
            raise
