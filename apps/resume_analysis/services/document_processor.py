import os
from django.core.files.storage import default_storage
from django.conf import settings

class DocumentProcessor:
    def __init__(self):
        self.upload_path = 'resumes'

    def save_document(self, file, file_id):
        """
        Save the uploaded document to storage
        """
        file_path = os.path.join(self.upload_path, str(file_id), file.name)
        return default_storage.save(file_path, file)

    def get_document(self, file_id):
        """
        Retrieve a document from storage
        """
        try:
            file_path = os.path.join(self.upload_path, str(file_id))
            return default_storage.open(file_path).read()
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")

    def delete_document(self, file_id):
        """
        Delete a document from storage
        """
        try:
            file_path = os.path.join(self.upload_path, str(file_id))
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
        except Exception as e:
            raise Exception(f"Error deleting document: {str(e)}")