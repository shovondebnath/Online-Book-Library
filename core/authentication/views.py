import random
import re
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import OTPVerificationForm, RegistrationForm


OTP_SESSION_KEY = 'pending_registration'
OTP_EXPIRY_SECONDS = 600
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def generate_otp():
    return str(random.randint(100000, 999999))



def _build_pending_registration(email, full_name, password, otp_code):
    return {
        'email': email,
        'full_name': full_name,
        'password': password,
        'otp': otp_code,
        'otp_created_at': time.time(),
    }


def _is_valid_email_format(email):
    return bool(EMAIL_REGEX.match(email))


def _is_otp_expired(created_at):
    try:
        created_at = float(created_at)
    except (TypeError, ValueError):
        return True
    return (time.time() - created_at) > OTP_EXPIRY_SECONDS


def _get_pending_registration(request):
    pending = request.session.get(OTP_SESSION_KEY)
    if not isinstance(pending, dict):
        return None

    required_keys = {'email', 'full_name', 'password', 'otp', 'otp_created_at'}
    if not required_keys.issubset(pending.keys()):
        return None
    return pending



@require_POST
def check_email_view(request):
    email = request.POST.get('email', '').strip().lower()

    if not email:
        return JsonResponse({
            'valid': False,
            'exists': False,
            'message': 'Email address is required.',
        })

    if not _is_valid_email_format(email):
        return JsonResponse({
            'valid': False,
            'exists': False,
            'message': 'Please enter a valid email address.',
        })

    if User.objects.filter(email=email).exists():
        return JsonResponse({
            'valid': True,
            'exists': True,
            'message': 'An account with this email already exists.',
        })

    return JsonResponse({'valid': True, 'exists': False, 'message': ''})


@require_POST
def check_login_email_view(request):
    email = request.POST.get('email', '').strip().lower()

    if not email:
        return JsonResponse({
            'valid': False,
            'exists': False,
            'message': 'Email address is required.',
        })

    if not _is_valid_email_format(email):
        return JsonResponse({
            'valid': False,
            'exists': False,
            'message': 'Please enter a valid email address.',
        })

    email_exists = User.objects.filter(email=email).exists()
    if not email_exists:
        return JsonResponse({
            'valid': True,
            'exists': False,
            'message': 'No account found with this email address.',
        })

    return JsonResponse({'valid': True, 'exists': True, 'message': ''})

