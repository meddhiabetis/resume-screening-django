import logging
from .pinecone_service import PineconeService

logger = logging.getLogger(__name__)

class SearchService:
    """Service for searching similar resumes using Pinecone.

    Attributes:
        pinecone_service (PineconeService): An instance of PineconeService to perform resume searches.
    """

    def __init__(self):
        """Initializes the SearchService with a PineconeService instance."""
        self.pinecone_service = PineconeService()

    def search_similar_resumes(self, query: str, section_type: str = 'full_text', limit: int = 10):
        """Search for resumes similar to the given query.

        Args:
            query (str): The search query to find similar resumes.
            section_type (str, optional): The type of section to search in. Defaults to 'full_text'.
            limit (int, optional): The maximum number of results to return. Defaults to 10.

        Returns:
            list: A list of similar resumes.

        Raises:
            Exception: If an error occurs during the search process.
        """
        try:
            results = self.pinecone_service.search_similar_resumes(query, section_type, limit)
            return results
        except Exception as e:
            logger.error(f"Error searching similar resumes: {str(e)}")
            raise