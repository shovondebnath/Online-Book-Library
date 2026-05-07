from django.contrib import admin
from .models import CreditWallet, CreditTransaction, Category, Book, MyBook, Borrow, ReadingProgress, Rating, Review, ReviewReaction

# Register your models here.

admin.site.register(CreditWallet)
admin.site.register(CreditTransaction)
admin.site.register(Category)
admin.site.register(Book)
admin.site.register(MyBook)
admin.site.register(Borrow)
admin.site.register(ReadingProgress)
admin.site.register(Rating)
admin.site.register(Review)
admin.site.register(ReviewReaction)