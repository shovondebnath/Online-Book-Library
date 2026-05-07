from uuid import uuid4 # Used for generating unique test file names in storage healthcheck

from django.conf import settings
from django.contrib import messages            # Used for displaying success/error/warning messages to users
from django.core.files.base import ContentFile # Used for creating in-memory file objects for storage testing
from django.db.models import Q 				   # Used for complex queries in book search (e.g. filtering by title and author with case-insensitive matching)
from django.http import JsonResponse
from django.urls import reverse 			   # Used for generating URLs based on view names, especially for redirects after form submissions
from django.shortcuts import redirect, render

from app.models import Book
from app.storage_backends import book_file_storage, cover_image_storage

from .forms import BookEntryForm, BookSearchForm



# Helper functions for user role and access control. 
# If return anonymous then user is not logged in.
# where the def is used? in the book_entry_view and book_update_view, to determine the current user's role for template rendering (permissions/UI hints).
def _get_user_role(user): 
	if not user.is_authenticated:
		return 'anonymous'
	if user.is_superuser and user.is_staff:
		return 'superuser'
	if (not user.is_superuser) and user.is_staff:
		return 'staff'
	return 'customer'



# Helper functions for access control to staff panel. 
# Returns a redirect response if access is denied, otherwise None.
def _has_staff_panel_access(user):
	return _get_user_role(user) in {'superuser', 'staff'}



# Helper function to enforce access control for staff panel views. 
# If the user is not authenticated or does not have staff access, 
# it returns a redirect response with an appropriate error message. 
# Otherwise, it returns None to indicate that access is allowed.
def _enforce_staff_panel_access(request):
	if not request.user.is_authenticated:
		messages.error(request, 'Please log in first.')
		return redirect('login_view')

	if not _has_staff_panel_access(request.user):
		messages.error(
			request,
			'Access denied. Only staff or superuser accounts can use this page.',
		)
		return redirect('home_view')

	return None



# Helper function to find a book based on search criteria.
def _find_book_from_search(cleaned_data):
	"""
	Resolve a single book from validated search input.

	Search priority:
	1) If `book_id` is provided, perform an exact id lookup and return immediately.
	2) Otherwise, search by exact title + exact author (both case-insensitive).

	Returns:
		(tuple) (book, warning_message)
		- book: `Book` instance or None
		- warning_message: str or None

	Behavior notes:
	- No match -> (None, None)
	- One match -> (book, None)
	- Multiple matches -> (first book by book_id, warning message)
	"""
	# Values come from form.cleaned_data, so they are already validated/sanitized
	# according to BookSearchForm rules.
	book_id = cleaned_data.get('book_id')
	title = cleaned_data.get('title')
	author = cleaned_data.get('author')

	# Fast path: explicit id lookup has highest priority and avoids ambiguity.
	if book_id:
		return Book.objects.filter(book_id=book_id).first(), None

	# Fallback path: exact title+author match (case-insensitive) to reduce false positives.
	matches = Book.objects.filter(
		Q(title__iexact=title),
		Q(author__iexact=author),
	).order_by('book_id')

	# Nothing matched the provided title/author pair.
	if not matches.exists():
		return None, None

	warning_message = None
	# If duplicates exist, keep deterministic behavior by selecting the first
	# record sorted by book_id and informing the caller via warning text.
	if matches.count() > 1:
		warning_message = (
			'Multiple books matched title and author. The first match was selected.'
		)

	return matches.first(), warning_message



# Views for book entry, book update, and storage healthcheck.
def book_entry_view(request):
	# Enforce that only authorized staff (panel users) can access this view.
	# _enforce_staff_panel_access returns either an HttpResponse (redirect/403)
	# when access is denied, or a falsy value when access is allowed.
	access_result = _enforce_staff_panel_access(request)
	if access_result:
		return access_result

	# Determine the current user's role for template rendering (permissions/UI hints).
	user_role = _get_user_role(request.user)

	# If the form is submitted, bind POST data and uploaded files to the form.
	if request.method == 'POST':
		# Pass actor=request.user to the form so it can apply actor-specific
		# validation or defaults (e.g. limiting selectable shelves or editors).
		form = BookEntryForm(request.POST, request.FILES, actor=request.user)
		# Validate the form; if valid, save but don't commit to attach extra fields.
		if form.is_valid():
			# commit=False returns an unsaved Book instance so we can set
			# fields not provided by the form (e.g. added_by) before saving.
			book = form.save(commit=False)
			book.added_by = request.user
			book.save()
			# Save any many-to-many relationships after the instance has a PK.
			form.save_m2m()
			# Provide user feedback and redirect back to the entry page.
			messages.success(request, 'Book added successfully.')
			return redirect('book_entry')
	else:
		# GET request: present an empty form. Provide actor for any display logic.
		form = BookEntryForm(actor=request.user)

	# Render the entry template with the bound/empty form and the user's role.
	return render(
		request,
		'book_entry.html',
		{
			'form': form,
			'user_role': user_role,
		},
	)



# The book update view allows staff users to search for an existing book and update its details.
def book_update_view(request):
	# Enforce staff-only access; non-staff are redirected by the helper.
	access_result = _enforce_staff_panel_access(request)
	if access_result:
		return access_result

	# Prepare view context: user role, search form, and placeholders for book/form.
	user_role = _get_user_role(request.user)
	search_form = BookSearchForm(request.GET or None)
	book = None
	form = None

	if request.method == 'POST':
		# Update submission: require a selected target book id from the search step.
		target_book_id = request.POST.get('target_book_id')

		if not target_book_id:
			messages.error(request, 'Please search and select a book before updating.')
			return redirect('book_update')

		# Fetch the existing book to update; bail out if missing.
		book = Book.objects.filter(book_id=target_book_id).first()
		if not book:
			messages.error(request, 'Selected book was not found.')
			return redirect('book_update')

		# Bind the submitted data to the update form with the existing instance.
		form = BookEntryForm(
			request.POST,
			request.FILES,
			actor=request.user,
			instance=book,
			for_update=True,
		)

		if form.is_valid():
			# Persist updates, preserving the original added_by attribution.
			updated_book = form.save(commit=False)
			updated_book.added_by = book.added_by
			updated_book.save()
			form.save_m2m()
			messages.success(request, f'Book #{updated_book.book_id} updated successfully.')
			return redirect(f"{reverse('book_update')}?book_id={updated_book.book_id}")
	else:
		# GET request: check if there is any search input before validating.
		has_search_input = any(
			(request.GET.get(field) or '').strip() for field in ('book_id', 'title', 'author')
		)

		if has_search_input and search_form.is_valid():
			# Resolve a book from the search criteria and report any warnings.
			book, warning_message = _find_book_from_search(search_form.cleaned_data)

			if warning_message:
				messages.warning(request, warning_message)

			if not book:
				messages.error(request, 'No matching book found.')
			else:
				# Populate the update form with the found book instance.
				form = BookEntryForm(
					actor=request.user,
					instance=book,
					for_update=True,
				)

	# Render the update page with search form, optional book/form, and user role.
	return render(
		request,
		'book_update.html',
		{
			'search_form': search_form,
			'form': form,
			'book': book,
			'user_role': user_role,
		},
	)


# The storage healthcheck view validates that the application is properly configured to interact with the underlying storage service (e.g. AWS S3 or Supabase Storage).
def storage_healthcheck_view(request):
	access_result = _enforce_staff_panel_access(request)
	if access_result:
		return access_result

	# Optional query flag to run a write/read/delete validation against storage buckets.
	run_write_test = request.GET.get('write_test') == '1'

	# Collect required configuration values to validate storage setup.
	required_values = {
		'AWS_ACCESS_KEY_ID': getattr(settings, 'AWS_ACCESS_KEY_ID', ''),
		'AWS_SECRET_ACCESS_KEY': getattr(settings, 'AWS_SECRET_ACCESS_KEY', ''),
		'AWS_S3_ENDPOINT_URL': getattr(settings, 'AWS_S3_ENDPOINT_URL', ''),
		'AWS_S3_REGION_NAME': getattr(settings, 'AWS_S3_REGION_NAME', ''),
		'SUPABASE_PROJECT_REF': getattr(settings, 'SUPABASE_PROJECT_REF', ''),
	}

	# Determine whether all required settings are present.
	missing = [key for key, value in required_values.items() if not value]
	configured = not missing

	# Prepare a response scaffold for configuration and bucket checks.
	result = {
		'configured': configured,
		'missing_settings': missing,
		'run_write_test': run_write_test,
		'upload_ready': False,
		'bucket_checks': [],
	}

	# If configuration is incomplete, return immediately with error status.
	if not configured:
		return JsonResponse(result, status=500)

	# Storage buckets to probe for initialization and optional write test.
	bucket_items = [
		('book-files', book_file_storage),
		('cover-image', cover_image_storage),
	]

	# Track overall write readiness across all buckets.
	all_ok = True
	for bucket_name, storage_factory in bucket_items:
		storage = storage_factory()
		# Initialize bucket result data; write test fields are filled if requested.
		bucket_result = {
			'bucket': bucket_name,
			'can_init_storage': True,
			'can_write': None,
			'error': None,
		}

		if run_write_test:
			# Attempt to write, verify existence, then delete a probe file.
			test_name = f"healthcheck/{uuid4().hex}.txt"
			try:
				saved_name = storage.save(test_name, ContentFile(b'supabase-storage-check'))
				bucket_result['can_write'] = storage.exists(saved_name)
				storage.delete(saved_name)
			except Exception as exc:
				bucket_result['can_write'] = False
				bucket_result['error'] = str(exc)
				all_ok = False

		result['bucket_checks'].append(bucket_result)

	if run_write_test:
		# Upload readiness requires all buckets to pass the write test.
		result['upload_ready'] = all_ok and all(item['can_write'] for item in result['bucket_checks'])
		status_code = 200 if result['upload_ready'] else 500
		return JsonResponse(result, status=status_code)

	# If not running write tests, configuration-only check passes.
	result['upload_ready'] = True
	return JsonResponse(result)
