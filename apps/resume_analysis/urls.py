from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings


app_name = 'resume_analysis'

urlpatterns = [
    path('upload/batch/', views.upload_resumes, name='upload_resumes'),
    path('upload-form/', views.upload_form, name='upload_form'),
    path('view/<uuid:file_id>/', views.view_resume, name='view_resume'),
    path('delete/<uuid:file_id>/', views.delete_resume, name='delete_resume'),
    path('extract/<uuid:file_id>/', views.extract_features, name='extract_features'),
    path('search/', views.search_similar_resumes, name='search_similar_resumes'),
    path('api/search/similar/', views.search_similar_resumes, name='api_search_similar_resumes'),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)