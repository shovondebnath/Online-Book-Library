from math import log1p
import random

from django.db.models import F, Q
from django.utils import timezone

from app.models import Book, Borrow, Category, MyBook, Rating, ReadingProgress
from recommendation_system.models import UserCategoryRead, UserSearchEvent


RECOMMENDATION_LIMIT = 8
RECOMMENDATION_PERSONALIZED_RATIO = 0.4
RECOMMENDATION_CANDIDATE_LIMIT = 200
SEARCH_EVENT_LIMIT = 20
SEARCH_CATEGORY_WEIGHT = 1.0
SEARCH_GENRE_WEIGHT = 0.5
CATEGORY_READ_WEIGHT = 1.5


def _parse_genres(raw_genres):
    return [genre.strip().lower() for genre in (raw_genres or '').split(',') if genre.strip()]


def _tokenize_search_query(query):
    return [token for token in (query or '').lower().split() if token]


def _collect_user_interaction_weights(user):
    weights = {}
    if not user or not user.is_authenticated:
        return weights

    def _add_weight(book_id, weight):
        weights[book_id] = weights.get(book_id, 0) + weight

    for rating in Rating.objects.filter(user=user).only('book_id', 'rating_value'):
        _add_weight(rating.book_id, rating.rating_value)

    for borrow in Borrow.objects.filter(user=user).only('book_id'):
        _add_weight(borrow.book_id, 3)

    for saved in MyBook.objects.filter(user=user).only('book_id'):
        _add_weight(saved.book_id, 2)

    for progress in ReadingProgress.objects.filter(user=user).only('book_id'):
        _add_weight(progress.book_id, 1)

    return weights


def _build_user_profile(user):
    weights = _collect_user_interaction_weights(user)
    category_weights = {}
    genre_weights = {}
    if weights:
        for book in (
            Book.objects.filter(book_id__in=weights.keys())
            .select_related('category')
            .only('book_id', 'category_id', 'genres')
        ):
            weight = weights.get(book.book_id, 0)
            if book.category_id:
                category_weights[book.category_id] = category_weights.get(book.category_id, 0) + weight
            for genre in _parse_genres(book.genres):
                genre_weights[genre] = genre_weights.get(genre, 0) + weight

    _apply_category_read_weights(user, category_weights)
    _apply_search_signals(user, category_weights, genre_weights)

    if not category_weights and not genre_weights:
        return None, None

    return category_weights, genre_weights


def _apply_category_read_weights(user, category_weights):
    if not user or not user.is_authenticated:
        return
    for entry in UserCategoryRead.objects.filter(user=user).only('category_id', 'read_count'):
        category_weights[entry.category_id] = (
            category_weights.get(entry.category_id, 0) + entry.read_count * CATEGORY_READ_WEIGHT
        )


def _apply_search_signals(user, category_weights, genre_weights):
    if not user or not user.is_authenticated:
        return

    search_queries = list(
        UserSearchEvent.objects.filter(user=user)
        .order_by('-created_at')
        .values_list('query', flat=True)[:SEARCH_EVENT_LIMIT]
    )
    if not search_queries:
        return

    token_weights = {}
    for query in search_queries:
        for token in _tokenize_search_query(query):
            token_weights[token] = token_weights.get(token, 0) + 1

    if not token_weights:
        return

    categories = list(Category.objects.all().only('id', 'name'))
    for token, weight in token_weights.items():
        for category in categories:
            name = (category.name or '').lower()
            if token in name:
                category_weights[category.id] = category_weights.get(category.id, 0) + weight * SEARCH_CATEGORY_WEIGHT
        genre_weights[token] = genre_weights.get(token, 0) + weight * SEARCH_GENRE_WEIGHT


def _top_weighted_keys(weight_map, limit):
    return [key for key, _ in sorted(weight_map.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _score_book_for_user(book, category_weights, genre_weights):
    score = 0
    score += category_weights.get(book.category_id, 0) * 2
    for genre in _parse_genres(book.genres):
        score += genre_weights.get(genre, 0)
    avg_rating = book.avg_rating or 0
    rating_count = book.rating_count or 0
    score += float(avg_rating)
    score += log1p(float(rating_count))
    return score


def _get_user_interacted_book_ids(user):
    if not user or not user.is_authenticated:
        return set()
    book_ids = set(Rating.objects.filter(user=user).values_list('book_id', flat=True))
    book_ids.update(Borrow.objects.filter(user=user).values_list('book_id', flat=True))
    book_ids.update(MyBook.objects.filter(user=user).values_list('book_id', flat=True))
    book_ids.update(ReadingProgress.objects.filter(user=user).values_list('book_id', flat=True))
    return book_ids


def _get_personalized_recommendations(user, exclude_ids, base_queryset, limit):
    if limit <= 0:
        return []

    category_weights, genre_weights = _build_user_profile(user)
    if not category_weights and not genre_weights:
        return []

    category_ids = _top_weighted_keys(category_weights or {}, 4)
    genre_tokens = _top_weighted_keys(genre_weights or {}, 8)
    if not category_ids and not genre_tokens:
        return []

    filters = Q()
    if category_ids:
        filters |= Q(category_id__in=category_ids)
    for genre in genre_tokens:
        filters |= Q(genres__icontains=genre)

    candidates = list(
        base_queryset.filter(filters)
        .exclude(book_id__in=exclude_ids)
        [:RECOMMENDATION_CANDIDATE_LIMIT]
    )
    if not candidates:
        return []

    scored = [
        (_score_book_for_user(book, category_weights, genre_weights), book)
        for book in candidates
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [book for _, book in scored[:limit]]


def get_openbook_recommendations(user, current_book, base_queryset, limit=RECOMMENDATION_LIMIT):
    available_queryset = base_queryset.exclude(book_id=current_book.book_id)
    if not user or not user.is_authenticated:
        return list(available_queryset.order_by('?')[:limit])

    interacted_ids = _get_user_interacted_book_ids(user)
    exclude_ids = set(interacted_ids)
    exclude_ids.add(current_book.book_id)

    personalized_target = max(1, int(limit * RECOMMENDATION_PERSONALIZED_RATIO))
    personalized = _get_personalized_recommendations(user, exclude_ids, available_queryset, personalized_target)
    personalized_ids = {book.book_id for book in personalized}
    remaining_random = limit - len(personalized)
    if remaining_random < 0:
        remaining_random = 0

    random_queryset = available_queryset.exclude(book_id__in=exclude_ids | personalized_ids)
    random_books = list(random_queryset.order_by('?')[:remaining_random])
    random.shuffle(random_books)

    combined = personalized + random_books
    if len(combined) < limit:
        fill_needed = limit - len(combined)
        fill_queryset = available_queryset.exclude(
            book_id__in=exclude_ids | personalized_ids | {book.book_id for book in random_books}
        )
        combined.extend(list(fill_queryset.order_by('?')[:fill_needed]))

    return combined


def record_search_event(user, query):
    if not user or not user.is_authenticated:
        return
    cleaned = (query or '').strip()
    if not cleaned:
        return
    UserSearchEvent.objects.create(user=user, query=cleaned[:255])


def record_category_read(user, category_id):
    if not user or not user.is_authenticated or not category_id:
        return
    entry, created = UserCategoryRead.objects.get_or_create(
        user=user,
        category_id=category_id,
        defaults={'read_count': 1},
    )
    if not created:
        UserCategoryRead.objects.filter(id=entry.id).update(
            read_count=F('read_count') + 1,
            last_read_at=timezone.now(),
        )
