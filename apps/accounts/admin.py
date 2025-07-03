from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

class ProfileInline(admin.StackedInline):
    """
    Inline admin interface for the Profile model.

    Attributes:
        model: The model to be used for the inline.
        can_delete: Boolean indicating if the inline can be deleted.
        verbose_name_plural: The plural name for the inline in the admin interface.
    """
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for the User model, including the Profile inline.

    Attributes:
        inlines: A tuple of inline models to be displayed in the admin interface.
    """
    inlines = (ProfileInline,)


# Re-register UserAdmin to replace the default User admin interface
admin.site.unregister(User)
admin.site.register(User, UserAdmin)