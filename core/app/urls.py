from django.urls import path
from . import views

urlpatterns = [
    path('support/', views.support_view, name='support_view'),
    path('about/', views.about_view, name='about_view'),
]