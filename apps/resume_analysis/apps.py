from django.apps import AppConfig

class ResumeAnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.resume_analysis'

    def ready(self):
        try:
            from .utils.env_checker import verify_environment
            verify_environment()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Environment verification failed: {str(e)}")