from django.urls import path
from . import views

urlpatterns = [
    path('registration/', views.register_view, name='register'),
    path('verify-otp/', views.otp_verify_view, name='otp_verify'),
    path('check-email/', views.check_email_view, name='check_email'),
    path('check-login-email/', views.check_login_email_view, name='check_login_email'),
    path('login/', views.auth_login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
]
