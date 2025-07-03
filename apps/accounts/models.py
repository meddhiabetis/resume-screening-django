from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    """
    A model representing a user profile.

    Attributes:
        user (OneToOneField): The user associated with this profile.
        company (str): The company name of the user.
        job_title (str): The job title of the user.
        created_at (DateTimeField): The timestamp when the profile was created.
        updated_at (DateTimeField): The timestamp when the profile was last updated.
        gmail_access_token (str): The access token for Gmail API.
        gmail_refresh_token (str): The refresh token for Gmail API.
        gmail_token_expiry (DateTimeField): The expiry time of the Gmail access token.
        gmail_email (EmailField): The Gmail email address of the user.
        gmail_connected (bool): Indicates if the Gmail account is connected.
        gmail_fetch_enabled (bool): Indicates if Gmail fetching is enabled.
        gmail_fetch_interval (PositiveIntegerField): The interval for fetching Gmail in minutes.
        last_gmail_fetch (DateTimeField): The timestamp of the last Gmail fetch.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    gmail_access_token = models.CharField(max_length=512, blank=True, null=True)
    gmail_refresh_token = models.CharField(max_length=512, blank=True, null=True)
    gmail_token_expiry = models.DateTimeField(blank=True, null=True)
    gmail_email = models.EmailField(blank=True, null=True)
    gmail_connected = models.BooleanField(default=False)
    gmail_fetch_enabled = models.BooleanField(default=False)
    gmail_fetch_interval = models.PositiveIntegerField(default=60)  # in minutes
    last_gmail_fetch = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """Return a string representation of the profile."""
        return f"{self.user.username}'s profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a Profile instance for a newly created User.

    Args:
        sender (Model): The model class that sent the signal.
        instance (User): The instance of the User that was created.
        created (bool): A boolean indicating if a new record was created.
        **kwargs: Additional keyword arguments.
    """
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the Profile instance when the User instance is saved.

    Args:
        sender (Model): The model class that sent the signal.
        instance (User): The instance of the User that was saved.
        **kwargs: Additional keyword arguments.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()