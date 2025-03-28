from django.db import models
from django.contrib.auth.models import User
import uuid

class Resume(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]

    file_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')

    class Meta:
        db_table = 'resume_analysis_resume'
        verbose_name = 'Resume'
        verbose_name_plural = 'Resumes'

    def __str__(self):
        return f"{self.original_filename} ({self.status})"

class ResumeContent(models.Model):
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, primary_key=True)
    raw_text = models.TextField()
    structured_data = models.JSONField(default=dict)
    extracted_features = models.JSONField(default=dict, null=True)
    last_processed = models.DateTimeField(auto_now=True)
    processing_error = models.TextField(null=True, blank=True)  # Add this field

    class Meta:
        db_table = 'resume_analysis_resumecontent'
        verbose_name = 'Resume Content'
        verbose_name_plural = 'Resume Contents'

    def extract_features(self):
        """Extract features using LLM"""
        from .services.llm_processor import LLMProcessor
        
        try:
            processor = LLMProcessor()
            features = processor.extract_resume_features(self.raw_text)
            
            if "error" in features:
                self.processing_error = features["error"]
                self.save()
                raise Exception(features["error"])
            
            self.extracted_features = features
            self.processing_error = None
            self.save()
            return features
            
        except Exception as e:
            self.processing_error = str(e)
            self.save()
            raise