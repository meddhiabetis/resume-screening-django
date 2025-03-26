from django.urls import path
from . import views

app_name = 'resume_analysis'  # This is important!

urlpatterns = [
    path('upload/', views.upload_resume, name='upload_resume'),
    path('upload-form/', views.upload_form, name='upload_form'),
    path('view/<uuid:file_id>/', views.view_resume, name='view_resume'),
    path('delete/<uuid:file_id>/', views.delete_resume, name='delete_resume'),
]