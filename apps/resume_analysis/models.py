import datetime
import uuid
from django.contrib.auth.models import User
from django.db import models
from .services.llm_processor import LLMProcessor

class Resume(models.Model):
    """
    Model representing a resume uploaded by a user.

    Attributes:
        file_id (UUIDField): Unique identifier for the resume.
        user (ForeignKey): The user who uploaded the resume.
        original_filename (CharField): The original filename of the uploaded resume.
        upload_date (DateTimeField): The date and time when the resume was uploaded.
        status (CharField): The processing status of the resume.
    """
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    ]

    file_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="processing"
    )

    class Meta:
        db_table = "resume_analysis_resume"
        verbose_name = "Resume"
        verbose_name_plural = "Resumes"

    def __str__(self):
        """Return a string representation of the resume."""
        return f"{self.original_filename} ({self.status})"


class ResumeContent(models.Model):
    """
    Model representing the content of a resume.

    Attributes:
        resume (OneToOneField): The associated resume.
        raw_text (TextField): The raw text extracted from the resume.
        structured_data (JSONField): Structured data extracted from the resume.
        extracted_features (JSONField): Features extracted from the resume.
        last_processed (DateTimeField): The date and time when the resume was last processed.
        processing_error (TextField): Any error encountered during processing.
        upload_date (DateTimeField): The date and time when the content was uploaded.
        uploaded_by (CharField): The name of the user who uploaded the content.
    """
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, primary_key=True)
    raw_text = models.TextField()
    structured_data = models.JSONField(default=dict)
    extracted_features = models.JSONField(default=dict, null=True)
    last_processed = models.DateTimeField(auto_now=True)
    processing_error = models.TextField(null=True, blank=True)
    upload_date = models.DateTimeField(default=datetime.datetime.utcnow)
    uploaded_by = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = "resume_analysis_resumecontent"
        verbose_name = "Resume Content"
        verbose_name_plural = "Resume Contents"

    def extract_features(self):
        """
        Extract features from the resume using an LLM processor with retries.

        Raises:
            Exception: If an error occurs during feature extraction.
        
        Returns:
            dict: The extracted features from the resume.
        """
        try:
            processor = LLMProcessor()
            features = processor.extract_resume_features(self.raw_text, max_retries=3)

            if "error" in features:
                self.processing_error = (
                    f"{features['error']}: {features.get('details', '')}"
                )
                self.save()
                raise Exception(self.processing_error)

            self.extracted_features = features
            self.processing_error = None
            self.save()
            return features

        except Exception as e:
            self.processing_error = str(e)
            self.save()
            raise
