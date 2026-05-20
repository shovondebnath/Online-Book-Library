import random
import re
import time
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from app.models import CreditWallet
from .forms import OTPVerificationForm, RegistrationForm


OTP_SESSION_KEY = 'pending_registration'
OTP_EXPIRY_SECONDS = 600
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def generate_otp():
    return str(random.randint(100000, 999999))


def _ensure_credit_wallet(user):
    if not user or user.is_staff:
        return None
    wallet, _ = CreditWallet.objects.get_or_create(
        user=user,
        defaults={'balance': Decimal('500.00')},
    )
    return wallet



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


def _email_in_use(email):
    return User.objects.filter(
        Q(email__iexact=email) | Q(username__iexact=email)
    ).exists()


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

    if _email_in_use(email):
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

    email_exists = _email_in_use(email)
    if not email_exists:
        return JsonResponse({
            'valid': True,
            'exists': False,
            'message': 'No account found with this email address.',
        })

    return JsonResponse({'valid': True, 'exists': True, 'message': ''})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home_view')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            full_name = form.cleaned_data['full_name']
            raw_password = form.cleaned_data['password']
            hashed_password = make_password(raw_password)

            otp_code = generate_otp()
            pending = _build_pending_registration(
                email, full_name, hashed_password, otp_code
            )
            request.session[OTP_SESSION_KEY] = pending
            request.session['otp_email'] = email

            send_mail(
                subject='Your DigiShelf Verification Code',
                message=(
                    f"Hi {full_name},\n\n"
                    f"Your one-time verification code is: {otp_code}\n\n"
                    f"This code expires in 10 minutes.\n\n"
                    f"If you didn't request this, please ignore this email.\n\n"
                    f"The DigiShelf Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, f"A 6-digit code has been sent to {email}.")
            return redirect('otp_verify')

        return render(request, 'registration.html', {'form': form})

    form = RegistrationForm()
    return render(request, 'registration.html', {'form': form})


def otp_verify_view(request):
    if request.user.is_authenticated:
        return redirect('home_view')

    pending = _get_pending_registration(request)
    if not pending:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register')

    email = pending['email']

    if request.method == 'POST':
        if 'resend' in request.POST:
            return _resend_otp(request, pending)

        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']

            if _is_otp_expired(pending['otp_created_at']):
                messages.error(request, 'Your OTP has expired. Please request a new one.')
                return render(request, 'otp_verify.html', {'form': form, 'email': email})

            if pending['otp'] != entered_otp:
                messages.error(request, 'Invalid OTP. Please try again.')
                return render(request, 'otp_verify.html', {'form': form, 'email': email})

            if _email_in_use(email):
                request.session.pop(OTP_SESSION_KEY, None)
                request.session.pop('otp_email', None)
                messages.error(
                    request,
                    'An account with this email already exists. Please log in.',
                )
                return redirect('login_view')

            name_parts = pending['full_name'].strip().split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            user = User.objects.create(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=pending['password'],
                is_staff=False,
                is_superuser=False,
            )

            _ensure_credit_wallet(user)

            request.session.pop(OTP_SESSION_KEY, None)
            request.session.pop('otp_email', None)

            auth_login(request, user)
            messages.success(request, f'Welcome to DigiShelf, {first_name}!')
            return redirect('home_view')
    else:
        form = OTPVerificationForm()

    return render(request, 'otp_verify.html', {'form': form, 'email': email})


def _resend_otp(request, pending):
    email = pending['email']

    if _is_otp_expired(pending['otp_created_at']):
        messages.info(request, 'Previous code expired. Sending a new code.')

    new_otp = generate_otp()
    pending['otp'] = new_otp
    pending['otp_created_at'] = time.time()
    request.session[OTP_SESSION_KEY] = pending

    send_mail(
        subject='Your new DigiShelf Verification Code',
        message=(
            f"Hi {pending['full_name']},\n\n"
            f"Your new verification code is: {new_otp}\n\n"
            f"This code expires in 10 minutes.\n\n"
            f"The DigiShelf Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    messages.success(request, 'A new OTP has been sent to your email.')
    return redirect('otp_verify')



def auth_login_view(request):
    if request.user.is_authenticated:
        return redirect('home_view')

    errors = {}
    email_value = ''

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        email_value = email

        if not email:
            errors['email'] = 'Email address is required.'
        elif not _is_valid_email_format(email):
            errors['email'] = 'Please enter a valid email address.'

        if not password:
            errors['password'] = 'Password is required.'

        if not errors:
            user = User.objects.filter(
                Q(email__iexact=email) | Q(username__iexact=email)
            ).first()

            if user is None or not user.check_password(password):
                errors['password'] = 'Incorrect email or password.'
            elif not user.is_active:
                errors['password'] = 'This account has been disabled.'
            else:
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                _ensure_credit_wallet(user)
                next_url = request.POST.get('next') or request.GET.get('next') or 'home_view'
                return redirect(next_url)

    return render(request, 'login.html', {
        'errors': errors,
        'email_value': email_value,
    })


def logout_view(request):
    auth_logout(request)
    return redirect('home_view')
