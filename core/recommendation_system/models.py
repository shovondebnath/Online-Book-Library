from django.conf import settings
from django.db import models

from app.models import Category


class UserSearchEvent(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='search_events')
	query = models.CharField(max_length=255)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.user_id}: {self.query}"


class UserCategoryRead(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='category_reads')
	category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='category_reads')
	read_count = models.PositiveIntegerField(default=0)
	last_read_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'category'], name='unique_user_category_read')
		]

	def __str__(self):
		return f"{self.user_id}: {self.category_id} ({self.read_count})"
