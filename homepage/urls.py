from django.urls import path
from .views import HomePageView, about, contact, signout, upload_resumes, analysis_results  # Import the analysis_results view function

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('signout/', signout, name='signout'),
    path('upload/', upload_resumes, name='upload_resumes'),
    path('analysis/', analysis_results, name='analysis_results'),  # Add the URL pattern for analysis_results
]
