from django.urls import path
from .views import HomePageView, about, contact, signout, analysis_results_single, analysis_results_multiple  # Updated import

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('signout/', signout, name='signout'),
    path('analysis/single/', analysis_results_single, name='analysis_results_single'),  # Update URL pattern for single resume analysis
    path('analysis/multiple/', analysis_results_multiple, name='analysis_results_multiple'),  # Update URL pattern for multiple resume analysis
]
