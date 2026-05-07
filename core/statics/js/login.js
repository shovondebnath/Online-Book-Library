// login.js

// ---------------------------------------------------------------------------
// Floating books background animation
// ---------------------------------------------------------------------------
function createFloatingBooks() {
    const container = document.getElementById('bg-animation');
    if (!container) return;
    const books = ['📖', '📚', '📕', '📗', '📘', '📙'];

    for (let i = 0; i < 28; i++) {
        const book = document.createElement('div');
        book.className = 'float-book';
        book.textContent = books[Math.floor(Math.random() * books.length)];

        book.style.left              = Math.random() * 100 + 'vw';
        book.style.animationDuration = (Math.random() * 14 + 14) + 's';
        book.style.animationDelay    = '-' + Math.random() * 20 + 's';
        book.style.fontSize          = (Math.random() * 18 + 24) + 'px';
        book.style.opacity           = Math.random() * 0.12 + 0.08;

        if (Math.random() > 0.5) {
            book.style.animation = 'floatBook 18s linear infinite reverse';
        }

        container.appendChild(book);
    }
}

// ---------------------------------------------------------------------------
// Password visibility toggle
// ---------------------------------------------------------------------------
function togglePassword() {
    const passwordField = document.getElementById('password');
    const eyeIcon       = document.getElementById('eye-icon');

    if (passwordField.type === 'password') {
        passwordField.type  = 'text';
        eyeIcon.textContent = '🙈';
    } else {
        passwordField.type  = 'password';
        eyeIcon.textContent = '👁️';
    }
}

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

function getCsrfToken() {
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
}

/** Show or clear an error/success message below a field. */
function setFieldMessage(elementId, message, isSuccess = false) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = message;
    el.className   = message
        ? (isSuccess ? 'field-success' : 'field-error')
        : 'field-error'; // empty but keeps layout reserved
}

/** Mirrors the regex used in login_view._is_valid_email_format */
function isValidEmailFormat(email) {
    return /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(email);
}

// ---------------------------------------------------------------------------
// Live email validation (format + backend existence check)
// ---------------------------------------------------------------------------

async function verifyLoginEmailOnServer(email) {
    const url = window.CHECK_LOGIN_EMAIL_URL;
    if (!url) return;

    const body = new URLSearchParams({ email });

    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken(),
            },
            body,
        });

        if (!resp.ok) return;

        const data = await resp.json();
        if (!data.valid) {
            setFieldMessage('email-error', data.message || 'Please enter a valid email address.');
            return;
        }

        if (!data.exists) {
            setFieldMessage('email-error', data.message || 'No account found with this email address.');
            return;
        }

        setFieldMessage('email-error', '');
    } catch (err) {
        console.warn('Login email check failed:', err);
    }
}

function validateEmailField(email) {
    if (!email) {
        setFieldMessage('email-error', '');
        return;
    }

    if (!isValidEmailFormat(email)) {
        setFieldMessage('email-error', 'Please enter a valid email address.');
        return;
    }

    verifyLoginEmailOnServer(email);
}

const debouncedValidateEmail = debounce(function (email) {
    validateEmailField(email);
}, 400);

// ---------------------------------------------------------------------------
// Form submission guard
// ---------------------------------------------------------------------------

function handleLoginSubmit(e) {
    const emailEl    = document.getElementById('email');
    const passwordEl = document.getElementById('password');
    let blocked      = false;

    if (!emailEl.value.trim()) {
        setFieldMessage('email-error', 'Email address is required.');
        blocked = true;
    } else if (!isValidEmailFormat(emailEl.value.trim())) {
        setFieldMessage('email-error', 'Please enter a valid email address.');
        blocked = true;
    }

    if (!passwordEl.value) {
        setFieldMessage('password-error', 'Password is required.');
        blocked = true;
    }

    if (blocked) {
        e.preventDefault();
        return;
    }

    // Visual feedback while the request is in-flight
    const btn = document.getElementById('login-btn');
    if (btn) {
        btn.textContent = 'Signing in…';
        btn.disabled    = true;
    }
}

// ---------------------------------------------------------------------------
// Initialise
// ---------------------------------------------------------------------------

window.addEventListener('DOMContentLoaded', function () {
    createFloatingBooks();

    // --- Live email format validation ---
    const emailInput = document.getElementById('email');
    if (emailInput) {
        emailInput.addEventListener('input', function () {
            debouncedValidateEmail(this.value.trim());
        });

        emailInput.addEventListener('blur', function () {
            validateEmailField(this.value.trim()); // immediate on blur
        });

        // Clear the password-error banner when the user starts correcting their
        // password (it says "Incorrect email or password" — once they edit either
        // field it's stale).
        emailInput.addEventListener('input', function () {
            if (document.activeElement !== emailInput) {
                return;
            }
            const pwErr = document.getElementById('password-error');
            if (pwErr && pwErr.textContent.includes('Incorrect')) {
                setFieldMessage('password-error', '');
            }
        });
    }

    const passwordInput = document.getElementById('password');
    if (passwordInput) {
        passwordInput.addEventListener('input', function () {
            if (document.activeElement !== passwordInput) {
                return;
            }
            // Clear "required" or "Incorrect" message once they start typing
            setFieldMessage('password-error', '');
        });
    }

    // --- Form submit guard ---
    const form = document.getElementById('login-form');
    if (form) {
        form.addEventListener('submit', handleLoginSubmit);
    }

    console.log('%c✅ DigiShelf login ready — live email validation + inline errors active.',
        'color:#4b5f61; font-size:14px; font-weight:bold');
});