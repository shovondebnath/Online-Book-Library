from django.contrib.auth.models import User
from django.db import models

from .storage_backends import book_file_storage, cover_image_storage

# Create your models here.


# -------------------------
# CREDIT WALLET
# -------------------------
class CreditWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.balance}"


# -------------------------
# CREDIT TRANSACTION
# -------------------------
class CreditTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('ADD', 'Add'),
        ('DEDUCT', 'Deduct'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    reference_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


# -------------------------
# CATEGORY
# -------------------------
class Category(models.Model):
    name = models.CharField(max_length=255)
    ml_code = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


# -------------------------
# BOOK
# -------------------------
class Book(models.Model):
    book_id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    description = models.TextField()

    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    genres = models.CharField(max_length=200)
    credit_cost_for_7_days = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_cost_for_14_days = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_cost_for_20_days = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_cost_for_30_days = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    borrow_duration_days = models.IntegerField()
    book_paid = models.BooleanField(default=True)

    file_path = models.FileField(storage=book_file_storage, upload_to='books/')
    cover_image = models.ImageField(storage=cover_image_storage, upload_to='covers/')

    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# -------------------------
# MY BOOK LIBRARY
# -------------------------
class MyBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_books')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='saved_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'book'], name='unique_my_book')
        ]

    def __str__(self):
        return f"{self.user.username} saved {self.book.title}"


# -------------------------
# BORROW
# -------------------------
class Borrow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    borrow_date = models.DateTimeField()
    expiry_date = models.DateTimeField()

    credits_used = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)


# -------------------------
# READING PROGRESS
# -------------------------
class ReadingProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    last_page = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'book'], name='unique_progress')
        ]


# -------------------------
# RATING
# -------------------------
class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    rating_value = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'book'], name='unique_rating')
        ]


# -------------------------
# REVIEW
# -------------------------
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    parent_review = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
    )

    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


# -------------------------
# REVIEW REACTION
# -------------------------
class ReviewReaction(models.Model):
    class ReactionType(models.TextChoices):
        LIKE = 'LIKE', 'Like'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=ReactionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'review'], name='unique_review_reaction')
        ]
