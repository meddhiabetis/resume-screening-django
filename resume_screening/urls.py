from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from authentication.views import signin, signout, signup
from homepage.views import HomePageView, about, contact, analysis_results_single, analysis_results_multiple  # Updated import

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomePageView.as_view(), name='home'),  # Homepage view
    path('signin/', signin, name='signin'),  # Custom sign-in view
    path('signout/', signout, name='signout'),  # Custom sign-out view
    path('signup/', signup, name='signup'),  # Custom sign-up view
    path('about/', about, name='about'),  # About page
    path('contact/', contact, name='contact'),   # Include 'contact' URLs
    path('analysis/single/', analysis_results_single, name='analysis_results_single'),  # Update URL pattern and view name for single resume analysis
    path('analysis/multiple/', analysis_results_multiple, name='analysis_results_multiple'),  # Update URL pattern and view name for multiple resume analysis
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
