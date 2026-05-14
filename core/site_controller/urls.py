from django.urls import path

from . import views


urlpatterns = [
	path('', views.home_view, name='home_view'),
	path('home/', views.home_view, name='home_alias_view'),
	path('search/', views.search_page_view, name='search_page'),
	path('search/suggestions/', views.search_suggestions_view, name='search_suggestions'),
	path('reader/<int:book_id>/', views.ebook_reader_view, name='ebook_reader'),
	path('openbook/', views.openbook_view, name='openbook'),
	path('openbook/<int:book_id>/', views.openbook_view, name='openbook_detail'),
	path('borrow/<int:book_id>/', views.borrow_book_view, name='borrow_book'),
	path('my-books/', views.my_books_list_view, name='my_books_list'),
	path('my-books/add/<int:book_id>/', views.my_books_add_view, name='my_books_add'),
	path('my-books/remove/<int:book_id>/', views.my_books_remove_view, name='my_books_remove'),
]
