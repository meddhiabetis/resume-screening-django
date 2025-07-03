from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using either
    their username or email address.

    Inherits from Django's ModelBackend to extend the authentication process.

    Methods:
        authenticate(request, username, password, **kwargs):
            Authenticates a user based on username or email and password.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user using their username or email address.

        Args:
            request: The HTTP request object.
            username (str): The username or email address of the user.
            password (str): The password of the user.
            **kwargs: Additional keyword arguments.

        Returns:
            User object if authentication is successful, None otherwise.
        """
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password):
                return user
        return None