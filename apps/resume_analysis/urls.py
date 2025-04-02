from django.urls import path
from . import views

app_name = 'resume_analysis'

urlpatterns = [
    path('upload/', views.upload_resume, name='upload_resume'),
    path('upload-form/', views.upload_form, name='upload_form'),
    path('view/<uuid:file_id>/', views.view_resume, name='view_resume'),
    path('delete/<uuid:file_id>/', views.delete_resume, name='delete_resume'),
    path('extract/<uuid:file_id>/', views.extract_features, name='extract_features'),
    path('api/search/similar/', views.search_similar_resumes, name='search_similar_resumes'),
]