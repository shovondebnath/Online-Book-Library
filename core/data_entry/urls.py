from django.urls import path

from . import views

urlpatterns = [
	path('book-entry/', views.book_entry_view, name='book_entry'),
	path('book-update/', views.book_update_view, name='book_update'),
	path('storage-health/', views.storage_healthcheck_view, name='storage_health'),
]