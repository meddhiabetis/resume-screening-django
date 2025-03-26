from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/dashboard/', permanent=True), name='home'),  # Changed this line
    path('dashboard/', include(('apps.accounts.urls', 'accounts'), namespace='accounts')),  # Changed this line
    path('resume/', include(('apps.resume_analysis.urls', 'resume_analysis'), namespace='resume_analysis')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)