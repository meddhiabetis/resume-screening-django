from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class UserRegisterForm(UserCreationForm):
    """Form for user registration, extending the default UserCreationForm.

    Attributes:
        email (forms.EmailField): The email field for the user.
    """
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class UserUpdateForm(forms.ModelForm):
    """Form for updating user information.

    Attributes:
        email (forms.EmailField): The email field for the user.
    """
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']


class GmailFetchForm(forms.Form):
    """Form for fetching Gmail messages based on specified criteria.

    Attributes:
        subject (forms.CharField): The subject filter for the emails (optional).
        before (forms.DateField): The date before which emails should be fetched.
        after (forms.DateField): The date after which emails should be fetched.
    """
    subject = forms.CharField(label="Subject", required=False)
    before = forms.DateField(label="Before", required=True, widget=forms.DateInput(attrs={"type": "date"}))
    after = forms.DateField(label="After", required=True, widget=forms.DateInput(attrs={"type": "date"}))


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information.

    Attributes:
        company (str): The company name of the user.
        job_title (str): The job title of the user.
        gmail_fetch_enabled (bool): Flag indicating if Gmail fetching is enabled.
        gmail_fetch_interval (int): The interval for fetching Gmail messages.
    """
    class Meta:
        model = Profile
        fields = ['company', 'job_title', 'gmail_fetch_enabled', 'gmail_fetch_interval']