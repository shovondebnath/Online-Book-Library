// registration.js

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

/** Simple debounce — waits `delay` ms after the last call before firing. */
function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/** Read the Django CSRF token from the hidden form input. */
function getCsrfToken() {
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
}

/**
 * Show an error message below a field.
 * @param {string} elementId - The id of the <span> that holds the message.
 * @param {string} message   - Text to display (empty string clears the error).
 * @param {boolean} isSuccess - If true, render in green (e.g. "looks good").
 */
function setFieldMessage(elementId, message, isSuccess = false) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent  = message;
    el.className    = message
        ? (isSuccess ? 'field-success' : 'field-error')
        : 'field-error'; // keep class but empty text → invisible
}

// ---------------------------------------------------------------------------
// Email validation
// ---------------------------------------------------------------------------

/** Basic RFC-ish format check — mirrors the regex in views.py. */
function isValidEmailFormat(email) {
    return /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(email);
}

/**
 * AJAX call to /check-email/.
 * Tells the user immediately if the address is malformed or already registered.
 */
async function checkEmailExists(email) {
    const url = window.CHECK_EMAIL_URL;
    if (!url) return; // safety guard

    const body = new URLSearchParams({ email });

    try {
        const resp = await fetch(url, {
            method:  'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken':  getCsrfToken(),
            },
            body,
        });

        if (!resp.ok) return;
        const data = await resp.json();

        if (!data.valid) {
            setFieldMessage('email-error', data.message);
        } else if (data.exists) {
            setFieldMessage('email-error', data.message); // "already exists"
        } else {
            setFieldMessage('email-error', '✓ Email looks good', true);
        }
    } catch (err) {
        // Network error — fail silently; server-side validation still catches it.
        console.warn('Email check failed:', err);
    }
}

// Debounced version: fires 600 ms after the user stops typing.
const debouncedCheckEmail = debounce(function (email) {
    if (!email) {
        setFieldMessage('email-error', '');
        return;
    }

    // Instant format feedback before hitting the network.
    if (!isValidEmailFormat(email)) {
        setFieldMessage('email-error', 'Please enter a valid email address.');
        return;
    }

    // Format is fine — check existence on the backend.
    checkEmailExists(email);
}, 600);

// ---------------------------------------------------------------------------
// Password-match validation
// ---------------------------------------------------------------------------

function validatePasswordMatch() {
    const pw  = document.getElementById('password').value;
    const cpw = document.getElementById('confirm-password').value;

    if (!cpw) {
        // User hasn't started typing in confirm field yet — clear silently.
        setFieldMessage('confirm-password-error', '');
        return;
    }

    if (pw !== cpw) {
        setFieldMessage('confirm-password-error', 'Passwords do not match.');
    } else {
        setFieldMessage('confirm-password-error', '✓ Passwords match', true);
    }
}

// ---------------------------------------------------------------------------
// Form submission guard
// ---------------------------------------------------------------------------

/**
 * Prevents submission if there are known client-side errors.
 * Server-side validation is the real authority; this is just UX.
 */
function handleFormSubmit(e) {
    const emailEl    = document.getElementById('email');
    const emailError = document.getElementById('email-error');
    const cpwError   = document.getElementById('confirm-password-error');

    let blocked = false;

    // Block if email format is wrong
    if (emailEl && !isValidEmailFormat(emailEl.value.trim())) {
        setFieldMessage('email-error', 'Please enter a valid email address.');
        blocked = true;
    }

    // Block if there is a visible error on email (e.g. "already exists")
    if (emailError && emailError.textContent && !emailError.classList.contains('field-success')) {
        blocked = true;
    }

    // Block if passwords don't match
    const pw  = document.getElementById('password').value;
    const cpw = document.getElementById('confirm-password').value;
    if (pw && cpw && pw !== cpw) {
        setFieldMessage('confirm-password-error', 'Passwords do not match.');
        blocked = true;
    }

    if (blocked) {
        e.preventDefault();
    }
}

// ---------------------------------------------------------------------------
// Initialise
// ---------------------------------------------------------------------------

window.addEventListener('DOMContentLoaded', function () {
    createFloatingBooks();

    // --- Email live validation ---
    const emailInput = document.getElementById('email');
    if (emailInput) {
        emailInput.addEventListener('input', function () {
            debouncedCheckEmail(this.value.trim());
        });

        // Also check on blur so users who paste and tab away get feedback immediately.
        emailInput.addEventListener('blur', function () {
            const val = this.value.trim();
            if (!val) return;
            if (!isValidEmailFormat(val)) {
                setFieldMessage('email-error', 'Please enter a valid email address.');
            } else {
                checkEmailExists(val); // immediate, no debounce
            }
        });
    }

    // --- Password-match live validation ---
    const pwInput  = document.getElementById('password');
    const cpwInput = document.getElementById('confirm-password');

    if (cpwInput) {
        cpwInput.addEventListener('input', validatePasswordMatch);
    }
    if (pwInput) {
        // Re-check match if the user edits the original password after filling confirm.
        pwInput.addEventListener('input', function () {
            if (cpwInput && cpwInput.value) {
                validatePasswordMatch();
            }
        });
    }

    // --- Submission guard ---
    const form = document.getElementById('register-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    console.log('%c✅ DigiShelf registration ready — live email + password validation active.',
        'color:#4b5f61; font-size:14px; font-weight:bold');
});