from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def verify_environment():
    """Verify that all required environment variables are set"""
    required_vars = {
        'NEO4J_URI': settings.NEO4J_URI,
        'NEO4J_USER': settings.NEO4J_USER,
        'NEO4J_PASSWORD': settings.NEO4J_PASSWORD,
        'NEO4J_DATABASE': settings.NEO4J_DATABASE,
        'PINECONE_API_KEY': settings.PINECONE_API_KEY,
        'PINECONE_ENVIRONMENT': settings.PINECONE_ENVIRONMENT,
        'PINECONE_INDEX': settings.PINECONE_INDEX,
        'MISTRAL_API_KEY': settings.MISTRAL_API_KEY,
    }

    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing_vars.append(var_name)
            logger.error(f"Missing environment variable: {var_name}")

    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please check your .env file and make sure all required variables are set."
        )

    logger.info("All required environment variables are set")