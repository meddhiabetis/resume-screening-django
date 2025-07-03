from django.urls import path
from . import views

app_name = 'accounts' 

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  
    path("login/", views.login_view, name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("gmail/connect/", views.gmail_connect, name="gmail_connect"),
    path("gmail/callback/", views.gmail_callback, name="gmail_callback"),
    path('disconnect-gmail/', views.disconnect_gmail, name='disconnect_gmail'),
]