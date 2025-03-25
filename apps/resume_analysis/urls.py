from django.urls import path
from . import views

app_name = 'resume_analysis'

urlpatterns = [
    path('upload/', views.upload_resume, name='upload_resume'),
    path('view/<uuid:file_id>/', views.view_resume, name='view_resume'),
    path('delete/<uuid:file_id>/', views.delete_resume, name='delete_resume'),
]