from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator 
from django.db import transaction
from django.db.models import Avg, Case, Count, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from app.models import (
	Book,
	Borrow,
	Category,
	CreditTransaction,
	CreditWallet,
	MyBook,
	Rating,
	Review,
	ReviewReaction,
)
from recommendation_system.services import (
	get_openbook_recommendations,
	record_category_read,
	record_search_event,
)


COMMENTS_PER_PAGE = 8
MAX_REVIEW_LENGTH = 2000
MIN_BOOK_RATING = 1
MAX_BOOK_RATING = 5
SEARCH_RESULTS_PER_PAGE = 24
SEARCH_SUGGESTIONS_LIMIT = 8
SEARCH_MAX_QUERY_LENGTH = 120
BORROW_DURATION_DAYS = (7, 14, 20, 30)
BORROW_COST_FIELDS = {
	7: 'credit_cost_for_7_days',
	14: 'credit_cost_for_14_days',
	20: 'credit_cost_for_20_days',
	30: 'credit_cost_for_30_days',
}


def _books_with_ratings_queryset():
	return Book.objects.select_related('category').annotate(
		avg_rating=Avg('rating__rating_value'),
		rating_count=Count('rating', distinct=True),
	)


def _safe_comments_page(page_value):
	try:
		page = int(page_value)
	except (TypeError, ValueError):
		return 1
	return page if page > 0 else 1


def _comment_redirect(book_id, comments_page=1):
	query = {
		'show_comments': '1',
		'comments_page': _safe_comments_page(comments_page),
	}
	return f"{reverse('openbook_detail', args=[book_id])}?{urlencode(query)}"


def _login_redirect(request):
	messages.error(request, 'Please log in to continue.')
	query = urlencode({'next': request.get_full_path()})
	return redirect(f"{reverse('login_view')}?{query}")


def _borrow_cost_for_days(book, days):
	field_name = BORROW_COST_FIELDS.get(days)
	if not field_name:
		return None
	return getattr(book, field_name, None)


def _borrow_options(book):
	if not book.book_paid:
		return []

	options = []
	zero = Decimal('0')
	for days in BORROW_DURATION_DAYS:
		cost = _borrow_cost_for_days(book, days)
		if cost is None:
			continue
		if cost > zero:
			options.append({'days': days, 'cost': cost})

	return options


def _get_or_create_wallet(user):
	if not user or not user.is_authenticated or user.is_staff:
		return None
	wallet = CreditWallet.objects.select_for_update().filter(user=user).first()
	if wallet:
		return wallet
	return CreditWallet.objects.create(user=user)


def _get_active_borrow(user, book):
	if not user or not user.is_authenticated:
		return None

	now = timezone.now()
	Borrow.objects.filter(
		user=user,
		book=book,
		expiry_date__lte=now,
		is_active=True,
	).update(is_active=False)

	return (
		Borrow.objects.filter(
			user=user,
			book=book,
			expiry_date__gt=now,
			is_active=True,
		)
		.order_by('-expiry_date')
		.first()
	)


def _build_review_tree(book, user=None):
	all_reviews = list(
		Review.objects.filter(book=book)
		.select_related('user')
		.annotate(
			like_count=Count(
				'reactions',
				filter=Q(reactions__reaction_type=ReviewReaction.ReactionType.LIKE),
				distinct=True,
			),
		)
		.order_by('?')
	)

	user_reactions = {}
	if user and user.is_authenticated:
		user_reactions = {
			reaction.review_id: reaction.reaction_type
			for reaction in ReviewReaction.objects.filter(user=user, review__book=book)
		}

	children_by_parent = {}
	for review in all_reviews:
		review.reply_children = []
		review.user_reaction = user_reactions.get(review.id)
		children_by_parent.setdefault(review.parent_review_id, []).append(review)

	for review in all_reviews:
		review.reply_children = children_by_parent.get(review.id, [])

	return children_by_parent.get(None, [])


def _create_review(request, book, comments_page):
	if not request.user.is_authenticated:
		return _login_redirect(request)

	review_text = (request.POST.get('comment_text') or '').strip()
	parent_review_id = (request.POST.get('parent_review_id') or '').strip()

	if not review_text:
		messages.error(request, 'Comment cannot be empty.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	if len(review_text) > MAX_REVIEW_LENGTH:
		messages.error(request, f'Comment is too long. Keep it under {MAX_REVIEW_LENGTH} characters.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	parent_review = None
	if parent_review_id:
		parent_review = Review.objects.filter(id=parent_review_id, book=book).first()
		if not parent_review:
			messages.error(request, 'Reply target was not found.')
			return redirect(_comment_redirect(book.book_id, comments_page))

	Review.objects.create(
		user=request.user,
		book=book,
		review_text=review_text,
		parent_review=parent_review,
	)

	messages.success(request, 'Your comment was posted.')
	return redirect(_comment_redirect(book.book_id, comments_page))


def _edit_review(request, book, comments_page):
	if not request.user.is_authenticated:
		return _login_redirect(request)

	review_id = (request.POST.get('review_id') or '').strip()
	review_text = (request.POST.get('comment_text') or '').strip()
	review = Review.objects.filter(id=review_id, book=book).first()

	if not review:
		messages.error(request, 'Comment not found.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	if review.user_id != request.user.id:
		messages.error(request, 'You can edit only your own comments.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	if not review_text:
		messages.error(request, 'Edited comment cannot be empty.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	if len(review_text) > MAX_REVIEW_LENGTH:
		messages.error(request, f'Comment is too long. Keep it under {MAX_REVIEW_LENGTH} characters.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	review.review_text = review_text
	review.save(update_fields=['review_text'])
	messages.success(request, 'Comment updated successfully.')
	return redirect(_comment_redirect(book.book_id, comments_page))


def _delete_review(request, book, comments_page):
	if not request.user.is_authenticated:
		return _login_redirect(request)

	review_id = (request.POST.get('review_id') or '').strip()
	review = Review.objects.filter(id=review_id, book=book).first()

	if not review:
		messages.error(request, 'Comment not found.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	if review.user_id != request.user.id:
		messages.error(request, 'You can delete only your own comments.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	review.delete()
	messages.success(request, 'Comment deleted.')
	return redirect(_comment_redirect(book.book_id, comments_page))


def _toggle_review_reaction(request, book, comments_page):
	if not request.user.is_authenticated:
		return _login_redirect(request)

	review_id = (request.POST.get('review_id') or '').strip()
	reaction_type = (request.POST.get('reaction_type') or '').strip().upper()
	review = Review.objects.filter(id=review_id, book=book).first()

	if not review:
		messages.error(request, 'Comment not found for reaction.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	allowed_reactions = {
		ReviewReaction.ReactionType.LIKE,
	}
	if reaction_type not in allowed_reactions:
		messages.error(request, 'Invalid reaction type.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	reaction = ReviewReaction.objects.filter(user=request.user, review=review).first()
	if reaction and reaction.reaction_type == reaction_type:
		reaction.delete()
		messages.info(request, 'Reaction removed.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	if reaction:
		reaction.reaction_type = reaction_type
		reaction.save(update_fields=['reaction_type'])
		messages.success(request, 'Reaction updated.')
		return redirect(_comment_redirect(book.book_id, comments_page))

	ReviewReaction.objects.create(
		user=request.user,
		review=review,
		reaction_type=reaction_type,
	)
	messages.success(request, 'Reaction added.')
	return redirect(_comment_redirect(book.book_id, comments_page))


def _handle_review_post(request, book):
	comments_page = _safe_comments_page(request.POST.get('comments_page'))
	action = (request.POST.get('action') or 'create').strip().lower()

	if action == 'rate':
		return _rate_book(request, book)
	if action == 'edit':
		return _edit_review(request, book, comments_page)
	if action == 'delete':
		return _delete_review(request, book, comments_page)
	if action == 'react':
		return _toggle_review_reaction(request, book, comments_page)

	return _create_review(request, book, comments_page)


def _rate_book(request, book):
	if not request.user.is_authenticated:
		return _login_redirect(request)

	raw_rating_value = (request.POST.get('rating_value') or '').strip()
	try:
		rating_value = int(raw_rating_value)
	except (TypeError, ValueError):
		messages.error(request, 'Please select a valid star rating.')
		return redirect(reverse('openbook_detail', args=[book.book_id]))

	if rating_value == 0:
		Rating.objects.filter(user=request.user, book=book).delete()
		messages.info(request, 'Your rating was removed.')
		return redirect(reverse('openbook_detail', args=[book.book_id]))

	if rating_value < MIN_BOOK_RATING or rating_value > MAX_BOOK_RATING:
		messages.error(request, f'Rating must be between {MIN_BOOK_RATING} and {MAX_BOOK_RATING}.')
		return redirect(reverse('openbook_detail', args=[book.book_id]))

	_, created = Rating.objects.update_or_create(
		user=request.user,
		book=book,
		defaults={'rating_value': rating_value},
	)

	if created:
		messages.success(request, 'Thanks for rating this book!')
	else:
		messages.success(request, 'Your rating was updated successfully.')

	return redirect(reverse('openbook_detail', args=[book.book_id]))


def _normalize_search_query(raw_query):
	query = ' '.join((raw_query or '').split())
	return query[:SEARCH_MAX_QUERY_LENGTH]


def _search_books_queryset(query):
	tokens = [token for token in query.split(' ') if token]
	if not tokens:
		return _books_with_ratings_queryset().none()

	search_filter = Q()
	for token in tokens:
		token_filter = (
			Q(title__icontains=token)
			| Q(author__icontains=token)
			| Q(description__icontains=token)
			| Q(genres__icontains=token)
			| Q(category__name__icontains=token)
		)
		search_filter &= token_filter

	return (
		_books_with_ratings_queryset()
		.filter(search_filter)
		.annotate(
			search_priority=Case(
				When(title__iexact=query, then=Value(120)),
				When(author__iexact=query, then=Value(110)),
				When(title__istartswith=query, then=Value(100)),
				When(author__istartswith=query, then=Value(90)),
				When(title__icontains=query, then=Value(80)),
				When(author__icontains=query, then=Value(70)),
				default=Value(50),
				output_field=IntegerField(),
			)
		)
		.order_by('-search_priority', '-avg_rating', '-rating_count', '-created_at', '-book_id')
	)


def _search_recommendations(exclude_book_ids=None):
	queryset = _books_with_ratings_queryset().order_by('-created_at', '-book_id')
	if exclude_book_ids:
		queryset = queryset.exclude(book_id__in=exclude_book_ids)
	return queryset[:8]


def search_page_view(request):
	raw_query = request.GET.get('q')
	raw_query_normalized = ' '.join((raw_query or '').split())
	query = _normalize_search_query(raw_query)
	page_number = _safe_comments_page(request.GET.get('page'))
	if query and request.user.is_authenticated:
		record_search_event(request.user, query)

	error_message = None
	notice_message = None
	search_results = []
	total_results = 0
	results_page_obj = Paginator(Book.objects.none(), SEARCH_RESULTS_PER_PAGE).get_page(1)

	if raw_query_normalized and len(raw_query_normalized) > SEARCH_MAX_QUERY_LENGTH:
		notice_message = f'Search query was trimmed to {SEARCH_MAX_QUERY_LENGTH} characters.'

	if query:
		try:
			search_queryset = _search_books_queryset(query)
			total_results = search_queryset.count()
			results_page_obj = Paginator(search_queryset, SEARCH_RESULTS_PER_PAGE).get_page(page_number)
			search_results = list(results_page_obj.object_list)
		except Exception:
			error_message = 'Search is temporarily unavailable. Please try again in a moment.'
	elif raw_query:
		notice_message = notice_message or 'Please enter a valid keyword.'

	recommendations = _search_recommendations([book.book_id for book in search_results])

	return render(
		request,
		'search_page.html',
		{
			'query': query,
			'total_results': total_results,
			'search_results': search_results,
			'results_page_obj': results_page_obj,
			'recommendations': recommendations,
			'error_message': error_message,
			'notice_message': notice_message,
		},
	)


def search_suggestions_view(request):
	query = _normalize_search_query(request.GET.get('q'))
	if not query:
		return JsonResponse({'suggestions': []})

	try:
		book_candidates = (
			Book.objects.select_related('category')
			.filter(Q(title__icontains=query) | Q(author__icontains=query))
			.order_by(
				Case(
					When(title__istartswith=query, then=Value(0)),
					When(author__istartswith=query, then=Value(1)),
					default=Value(2),
					output_field=IntegerField(),
				),
				'-created_at',
				'-book_id',
			)[:SEARCH_SUGGESTIONS_LIMIT]
		)

		suggestions = []
		for book in book_candidates:
			suggestions.append(
				{
					'type': 'book',
					'label': book.title,
					'sub_label': f'by {book.author}',
					'url': reverse('openbook_detail', args=[book.book_id]),
				}
			)

		author_candidates = (
			Book.objects.filter(author__icontains=query)
			.values_list('author', flat=True)
			.distinct()[:SEARCH_SUGGESTIONS_LIMIT]
		)

		seen_authors = set()
		for author in author_candidates:
			clean_author = (author or '').strip()
			if not clean_author:
				continue

			normalized_author = clean_author.casefold()
			if normalized_author in seen_authors:
				continue

			seen_authors.add(normalized_author)
			suggestions.append(
				{
					'type': 'author',
					'label': clean_author,
					'sub_label': 'Author',
					'url': f"{reverse('search_page')}?{urlencode({'q': clean_author})}",
				}
			)

			if len(suggestions) >= SEARCH_SUGGESTIONS_LIMIT:
				break

		return JsonResponse({'suggestions': suggestions[:SEARCH_SUGGESTIONS_LIMIT]})
	except Exception:
		return JsonResponse({'suggestions': [], 'error': 'search_unavailable'}, status=200)


def borrow_book_view(request, book_id):
	if request.method != 'POST':
		return redirect(reverse('openbook_detail', args=[book_id]))

	if not request.user.is_authenticated:
		return _login_redirect(request)

	book = get_object_or_404(Book, book_id=book_id)
	if not book.book_paid:
		messages.info(request, 'This book is free to read.')
		return redirect(reverse('openbook_detail', args=[book.book_id]))

	active_borrow = _get_active_borrow(request.user, book)
	if active_borrow:
		expiry_display = timezone.localtime(active_borrow.expiry_date).strftime('%b %d, %Y')
		messages.info(request, f'You already borrowed this book until {expiry_display}.')
		return redirect(reverse('openbook_detail', args=[book.book_id]))

	raw_days = (request.POST.get('borrow_duration_days') or '').strip()
	try:
		duration_days = int(raw_days)
	except (TypeError, ValueError):
		messages.error(request, 'Please select a valid borrow duration.')
		return redirect(reverse('openbook_detail', args=[book.book_id]))

	cost = _borrow_cost_for_days(book, duration_days)
	if cost is None or cost <= Decimal('0'):
		messages.error(request, 'Selected borrow duration is not available for this book.')
		return redirect(reverse('openbook_detail', args=[book.book_id]))

	with transaction.atomic():
		wallet = _get_or_create_wallet(request.user)
		if not wallet:
			messages.error(request, 'You need a credit wallet to borrow books.')
			return redirect(reverse('openbook_detail', args=[book.book_id]))
		current_balance = Decimal(str(wallet.balance))
		if current_balance < cost:
			messages.error(request, 'You do not have enough credits to borrow this book.')
			return redirect(reverse('openbook_detail', args=[book.book_id]))

		wallet.balance = current_balance - cost
		wallet.save(update_fields=['balance', 'last_updated'])

		borrow_date = timezone.now()
		expiry_date = borrow_date + timedelta(days=duration_days)
		borrow = Borrow.objects.create(
			user=request.user,
			book=book,
			borrow_date=borrow_date,
			expiry_date=expiry_date,
			credits_used=cost,
			is_active=True,
		)
		CreditTransaction.objects.create(
			user=request.user,
			amount=cost,
			transaction_type='DEDUCT',
			reference_id=borrow.id,
		)

	expiry_display = timezone.localtime(expiry_date).strftime('%b %d, %Y')
	messages.success(request, f'Borrow confirmed. Access ends on {expiry_display}.')
	return redirect(reverse('openbook_detail', args=[book.book_id]))


def ebook_reader_view(request, book_id):
	book = get_object_or_404(Book, book_id=book_id)
	if book.book_paid:
		if not request.user.is_authenticated:
			return _login_redirect(request)
		active_borrow = _get_active_borrow(request.user, book)
		if not active_borrow:
			messages.error(request, 'Please borrow this book before opening the reader.')
			return redirect(reverse('openbook_detail', args=[book.book_id]))

	try:
		pdf_url = book.file_path.url if book.file_path else ''
	except Exception:
		pdf_url = ''

	if not pdf_url:
		messages.error(request, 'This book file is not available for reading right now.')
		return redirect(reverse('openbook_detail', args=[book.book_id]))

	username = request.user.username if request.user.is_authenticated else 'GUEST'
	return render(
		request,
		'ebook-reader.html',
		{
			'reader_book': book,
			'reader_pdf_url': pdf_url,
			'reader_title': book.title,
			'library_name': 'DigiShelf',
			'reader_watermark': f'DIGISHELF COPY · USER {username} · BOOK {book.book_id}',
			'lock_reader_url': True,
		},
	)


def my_books_list_view(request):
	if not request.user.is_authenticated:
		return JsonResponse({'ok': False, 'error': 'auth_required'}, status=401)

	my_book_entries = (
		MyBook.objects.filter(user=request.user)
		.select_related('book')
		.order_by('-created_at', '-id')
	)

	books_payload = []
	for entry in my_book_entries:
		book = entry.book
		cover_image_url = ''
		try:
			if book.cover_image:
				cover_image_url = book.cover_image.url
		except Exception:
			cover_image_url = ''

		books_payload.append(
			{
				'book_id': book.book_id,
				'title': book.title,
				'author': book.author,
				'cover_image_url': cover_image_url,
				'reader_url': reverse('ebook_reader', args=[book.book_id]),
				'openbook_url': reverse('openbook_detail', args=[book.book_id]),
				'remove_url': reverse('my_books_remove', args=[book.book_id]),
			}
		)

	return JsonResponse({'ok': True, 'books': books_payload})


def my_books_add_view(request, book_id):
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)

	if not request.user.is_authenticated:
		return JsonResponse({'ok': False, 'error': 'auth_required'}, status=401)

	book = get_object_or_404(Book, book_id=book_id)
	if book.book_paid and not _get_active_borrow(request.user, book):
		return JsonResponse({'ok': False, 'error': 'borrow_required'}, status=403)
	_, created = MyBook.objects.get_or_create(user=request.user, book=book)

	return JsonResponse(
		{
			'ok': True,
			'saved': created,
			'book': {
				'book_id': book.book_id,
				'title': book.title,
				'openbook_url': reverse('openbook_detail', args=[book.book_id]),
				'reader_url': reverse('ebook_reader', args=[book.book_id]),
			},
		}
	)


def my_books_remove_view(request, book_id):
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)

	if not request.user.is_authenticated:
		return JsonResponse({'ok': False, 'error': 'auth_required'}, status=401)

	deleted_count, _ = MyBook.objects.filter(
		user=request.user,
		book_id=book_id,
	).delete()

	return JsonResponse(
		{
			'ok': True,
			'removed': deleted_count > 0,
			'book_id': book_id,
		}
	)


def home_view(request):
	last_updated_books = (
		Book.objects.select_related('category')
		.order_by('-created_at', '-book_id')[:20]
	)
	books = Book.objects.select_related('category').order_by('?')

	categories = Category.objects.order_by('name').distinct()

	return render(
		request,
		'home.html',
		{
			'books': books,
			'last_updated_books': last_updated_books,
			'categories': categories,
		},
	)


def openbook_view(request, book_id=None):
	books_queryset = _books_with_ratings_queryset().order_by('-created_at', '-book_id')

	if book_id is not None:
		book = get_object_or_404(books_queryset, book_id=book_id)
	else:
		book = books_queryset.first()

	if not book:
		return render(
			request,
			'openbook.html',
			{
				'book': None,
				'genres_list': [],
				'recommendations': [],
				'top_level_reviews': [],
				'show_comments': False,
			},
		)

	if request.user.is_authenticated and book.category_id:
		record_category_read(request.user, book.category_id)

	if request.method == 'POST':
		return _handle_review_post(request, book)

	genres_list = [genre.strip() for genre in (book.genres or '').split(',') if genre.strip()]
	recommendations = get_openbook_recommendations(request.user, book, books_queryset)
	top_level_reviews = _build_review_tree(book, request.user)
	comments_page = _safe_comments_page(request.GET.get('comments_page'))
	reviews_paginator = Paginator(top_level_reviews, COMMENTS_PER_PAGE)
	reviews_page_obj = reviews_paginator.get_page(comments_page)
	show_comments = request.GET.get('show_comments') == '1'
	user_rating = None
	if request.user.is_authenticated:
		user_rating = (
			Rating.objects.filter(user=request.user, book=book)
			.values_list('rating_value', flat=True)
			.first()
		)
	active_borrow = _get_active_borrow(request.user, book) if book.book_paid else None
	can_read = not book.book_paid or active_borrow is not None
	borrow_options = _borrow_options(book)

	return render(
		request,
		'openbook.html',
		{
			'book': book,
			'genres_list': genres_list,
			'recommendations': recommendations,
			'top_level_reviews': list(reviews_page_obj.object_list),
			'reviews_page_obj': reviews_page_obj,
			'comments_page': reviews_page_obj.number,
			'show_comments': show_comments,
			'user_rating': user_rating,
			'active_borrow': active_borrow,
			'can_read': can_read,
			'borrow_options': borrow_options,
		},
	)
