from .pinecone_service import PineconeService
import logging

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        self.pinecone_service = PineconeService()

    def search_similar_resumes(self, query: str, section_type: str = 'full_text', limit: int = 10):
        try:
            results = self.pinecone_service.search_similar_resumes(query, section_type, limit)
            return results
        except Exception as e:
            logger.error(f"Error searching similar resumes: {str(e)}")
            raise