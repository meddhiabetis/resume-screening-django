import logging
from .pinecone_service import PineconeService
from django.core.files.storage import default_storage
import os

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.upload_path = 'resumes'
        self.pinecone_service = PineconeService()

    def save_document(self, file, file_id):
        """Save the uploaded document to storage and process vectors"""
        try:
            file_path = os.path.join(self.upload_path, str(file_id), file.name)
            saved_path = default_storage.save(file_path, file)
            
            try:
                self.pinecone_service.create_vectors_for_resume(file_id)
            except Exception as vector_error:
                logger.error(f"Vector generation failed for file_id {file_id}: {str(vector_error)}")
            
            return saved_path
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            raise Exception(f"Error saving document: {str(e)}")

    def get_document(self, file_id):
        """Retrieve a document from storage"""
        try:
            file_path = os.path.join(self.upload_path, str(file_id))
            return default_storage.open(file_path).read()
        except Exception as e:
            logger.error(f"Error retrieving document {file_id}: {str(e)}")
            raise Exception(f"Error retrieving document: {str(e)}")

    def delete_document(self, file_id):
        """Delete a document from storage and its associated vectors"""
        try:
            try:
                self.pinecone_service.index.delete(ids=[file_id])
            except Exception as vector_error:
                logger.error(f"Error deleting vectors for file_id {file_id}: {str(vector_error)}")

            file_path = os.path.join(self.upload_path, str(file_id))
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
        except Exception as e:
            logger.error(f"Error deleting document {file_id}: {str(e)}")
            raise Exception(f"Error deleting document: {str(e)}")