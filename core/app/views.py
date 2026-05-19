import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render

# Create your views here.

logger = logging.getLogger(__name__)

def support_view(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        topic = (request.POST.get('topic') or '').strip() or 'Support request'
        order_id = (request.POST.get('order_id') or '').strip()
        message = (request.POST.get('message') or '').strip()

        errors = []
        if len(name) < 2:
            errors.append('Please provide your full name.')
        if '@' not in email or '.' not in email:
            errors.append('Please provide a valid email address.')
        if len(message) < 10:
            errors.append('Please add more details to your message.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'support.html')

        subject = topic
        lines = [
            f'Name: {name}',
            f'Email: {email}',
        ]
        if order_id:
            lines.append(f'Order/Book ID: {order_id}')
        lines.append('')
        lines.append(message)

        try:
            EmailMessage(
                subject=subject,
                body='\n'.join(lines),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.EMAIL_HOST_USER],
                reply_to=[email],
            ).send()
            messages.success(request, 'Your support ticket was sent. We will reply soon.')
            return redirect('support_view')
        except Exception:
            logger.exception('Support email send failed')
            messages.error(request, 'We could not send your ticket right now. Please try again.')
            return render(request, 'support.html')

    return render(request, 'support.html')

def about_view(request):
    return render(request, 'about.html')
