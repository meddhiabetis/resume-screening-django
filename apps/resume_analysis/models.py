from django.db import models
from django.contrib.auth.models import User
import uuid

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file_id = models.UUIDField(default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('uploaded', 'Uploaded'),
            ('processing', 'Processing'),
            ('processed', 'Processed'),
            ('failed', 'Failed')
        ],
        default='uploaded'
    )

    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Resume'
        verbose_name_plural = 'Resumes'

    def __str__(self):
        return f"{self.original_filename} - {self.user.username}"

class ResumeContent(models.Model):
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE)
    raw_text = models.TextField()
    structured_data = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Resume Content'
        verbose_name_plural = 'Resume Contents'

    def __str__(self):
        return f"Content for {self.resume.original_filename}"