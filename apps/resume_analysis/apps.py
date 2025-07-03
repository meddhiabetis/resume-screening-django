import logging
from django.apps import AppConfig
from .utils.env_checker import verify_environment

class ResumeAnalysisConfig(AppConfig):
    """
    Configuration class for the Resume Analysis application.

    Attributes:
        default_auto_field (str): The default auto field type for models.
        name (str): The name of the application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.resume_analysis'

    def ready(self):
        """
        Perform environment verification when the application is ready.

        This method attempts to verify the environment by calling the
        `verify_environment` function from the utils.env_checker module.
        If an exception occurs, it logs an error message.
        """
        try:
            verify_environment()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Environment verification failed: {str(e)}")