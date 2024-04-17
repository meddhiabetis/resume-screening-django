from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from authentication.views import signin, signout, signup
from homepage.views import HomePageView, about, contact, upload_resumes, analysis_results  # Updated import

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomePageView.as_view(), name='home'),  # Homepage view
    path('signin/', signin, name='signin'),  # Custom sign-in view
    path('signout/', signout, name='signout'),  # Custom sign-out view
    path('signup/', signup, name='signup'),  # Custom sign-up view
    path('about/', about, name='about'),  # About page
    path('contact/', contact, name='contact'),   # Include 'contact' URLs
    path('upload/', upload_resumes, name='upload_resumes'),  # Updated URL pattern and view name
    path('analysis/', analysis_results, name='analysis_results'),  # Add the analysis_results URL pattern
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
