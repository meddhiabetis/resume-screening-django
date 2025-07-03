from django.apps import AppConfig

class AccountsConfig(AppConfig):
    """
    Configuration class for the User Accounts application.

    Attributes:
        default_auto_field (str): The default auto field type for models.
        name (str): The name of the application.
        verbose_name (str): A human-readable name for the application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'User Accounts'