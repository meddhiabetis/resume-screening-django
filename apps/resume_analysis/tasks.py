from celery import shared_task
from .models import Resume, ResumeContent
from .services.document_processor import DocumentProcessor
from .services.text_extractor import TextExtractor
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_resume(resume_id):
    try:
        resume = Resume.objects.get(id=resume_id)
        resume.status = 'processing'
        resume.save()

        # Get document from MongoDB
        doc_processor = DocumentProcessor()
        raw_content = doc_processor.get_document(resume.file_id)

        # Extract text based on file type
        text_extractor = TextExtractor()
        extracted_text = text_extractor.extract(raw_content, resume.original_filename)

        # Save extracted content
        ResumeContent.objects.create(
            resume=resume,
            raw_text=extracted_text,
            structured_data={},  # Will be populated in analysis phase
        )

        resume.status = 'processed'
        resume.save()

    except Exception as e:
        logger.error(f"Error processing resume {resume_id}: {str(e)}")
        resume.status = 'failed'
        resume.save()
        raise