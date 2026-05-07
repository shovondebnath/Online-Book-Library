from django import forms

from app.models import Book

# The BookEntryForm is used for both creating new book entries and updating existing ones. It includes conditional validation logic to handle the differences between paid and free books, as well as enforcing staff-only access to the form.
class BookEntryForm(forms.ModelForm):
    # Status options for whether a book is paid or free.
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('free', 'Free'),
    ]
    # Credit pricing fields stored on the Book model.
    CREDIT_FIELDS = (
        'credit_cost_for_7_days',
        'credit_cost_for_14_days',
        'credit_cost_for_20_days',
        'credit_cost_for_30_days',
    )

    # UI field to choose paid/free status in the form.
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial='paid',
        # This field is not stored directly on the model but controls validation and computed fields.
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    # The constructor accepts an optional 'actor' parameter to enforce access control based on the user's authentication and staff status. It also takes a 'for_update' flag to adjust validation rules when editing existing records.
    def __init__(self, *args, actor=None, **kwargs):
        # for_update toggles optional file inputs during edit.
        self.for_update = kwargs.pop('for_update', False)
        super().__init__(*args, **kwargs)
        # Actor is used to enforce staff-only access.
        self.actor = actor

        if self.for_update:
            # Do not require file uploads when editing existing records.
            self.fields['file_path'].required = False
            self.fields['cover_image'].required = False

        for field_name in self.CREDIT_FIELDS:
            # Credit fields are conditionally required based on status.
            self.fields[field_name].required = False

        if self.instance and self.instance.pk:
            # Prepopulate status based on stored paid/free flag.
            is_paid = self.instance.book_paid
            self.initial.setdefault('status', 'paid' if is_paid else 'free')

    # This helper method centralizes the logic for zeroing out credit costs when a book is marked as free, 
    # ensuring consistent behavior across both creation and update scenarios.
    @staticmethod
    def _apply_zero_credit_fields(cleaned_data):
        # Normalize credit pricing to zero for free books.
        cleaned_data['credit_cost_for_7_days'] = 0
        cleaned_data['credit_cost_for_14_days'] = 0
        cleaned_data['credit_cost_for_20_days'] = 0
        cleaned_data['credit_cost_for_30_days'] = 0

    # The clean method enforces that only authenticated staff or superusers can submit the form, and applies conditional validation rules based on whether the book is marked as paid or free. For free books, it automatically sets credit costs to zero and ignores borrowing duration. For paid books, it ensures that credit costs are non-negative and required.
    def clean(self):
        cleaned_data = super().clean()
        # Restrict access to authenticated staff or superusers.
        if self.actor and (
            not self.actor.is_authenticated
            or not (self.actor.is_staff or self.actor.is_superuser)
        ):
            raise forms.ValidationError(
                'Only staff or superuser users can submit book entries.'
            )

        # Apply conditional validation based on paid/free status.
        status = cleaned_data.get('status', 'paid')
        if status == 'free':
            # Free books ignore credit costs and borrowing duration.
            cleaned_data['book_paid'] = False
            cleaned_data['borrow_duration_days'] = 0
            self._apply_zero_credit_fields(cleaned_data)
            return cleaned_data

        # For paid books, enforce non-negative credit costs.
        for field_name in self.CREDIT_FIELDS:
            value = cleaned_data.get(field_name)
            if value is None:
                self.add_error(field_name, 'Please enter a credit cost.')
            elif value < 0:
                self.add_error(field_name, 'Credit cost cannot be negative.')

        if self.errors:
            return cleaned_data

        # Mark as paid and keep duration placeholder at zero.
        cleaned_data['book_paid'] = True
        # Duration is chosen by reader while borrowing; this catalog stores pricing slabs.
        cleaned_data['borrow_duration_days'] = 0

        return cleaned_data


    # The save method is overridden to ensure that computed fields based on the cleaned data are persisted to the model instance. 
    # This includes setting the book_paid flag and borrow_duration_days based on the form's logic, 
    # as well as ensuring that credit costs are saved correctly.
    def save(self, commit=True):
        instance = super().save(commit=False)

        # Persist computed fields from cleaned data.
        instance.book_paid = self.cleaned_data['book_paid']
        instance.borrow_duration_days = self.cleaned_data['borrow_duration_days']
        instance.credit_cost_for_7_days = self.cleaned_data.get('credit_cost_for_7_days', 0) or 0
        instance.credit_cost_for_14_days = self.cleaned_data.get('credit_cost_for_14_days', 0) or 0
        instance.credit_cost_for_20_days = self.cleaned_data.get('credit_cost_for_20_days', 0) or 0
        instance.credit_cost_for_30_days = self.cleaned_data.get('credit_cost_for_30_days', 0) or 0

        if commit:
            # Save model and many-to-many relationships when requested.
            instance.save()
            self.save_m2m()

        return instance

    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'description',
            'category',
            'genres',
            'credit_cost_for_7_days',
            'credit_cost_for_14_days',
            'credit_cost_for_20_days',
            'credit_cost_for_30_days',
            'file_path',
            'cover_image',
        ]
        widgets = {
            'title': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter book title'}
            ),
            'author': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter author name'}
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Write a short description of the book',
                }
            ),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'genres': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Example: Romance, Fiction'}
            ),
            'credit_cost_for_7_days': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Credit cost for 7 days',
                    'step': '0.01',
                    'min': '0',
                }
            ),
            'credit_cost_for_14_days': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Credit cost for 14 days',
                    'step': '0.01',
                    'min': '0',
                }
            ),
            'credit_cost_for_20_days': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Credit cost for 20 days',
                    'step': '0.01',
                    'min': '0',
                }
            ),
            'credit_cost_for_30_days': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Credit cost for 30 days',
                    'step': '0.01',
                    'min': '0',
                }
            ),
            'file_path': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


"""The BookSearchForm provides a flexible interface for searching the book 
catalog by either primary key or a combination of title and author. 
It includes validation logic to ensure that search queries are well-formed 
and that users provide sufficient information for a meaningful search."""
class BookSearchForm(forms.Form):
    # Search by primary key.
    book_id = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Search by Book ID',
                'min': '1',
            }
        ),
    )
    # Search by title (requires author too).
    title = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Or search by title'}
        ),
    )
    # Search by author (requires title too).
    author = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'With author name'}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        # Normalize inputs and enforce valid search combinations.
        book_id = cleaned_data.get('book_id')
        title = (cleaned_data.get('title') or '').strip()
        author = (cleaned_data.get('author') or '').strip()

        cleaned_data['title'] = title
        cleaned_data['author'] = author

        # Allow search by ID alone.
        if book_id:
            return cleaned_data

        # Allow search by both title and author.
        if title and author:
            return cleaned_data

        # Otherwise, reject the query.
        raise forms.ValidationError(
            'Search using Book ID, or provide both title and author.'
        )
