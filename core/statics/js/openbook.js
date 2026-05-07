function openCommentModal() {
    const modal = document.getElementById('commentModal');
    if (!modal) {
        return;
    }

    modal.style.display = 'flex';
    requestAnimationFrame(() => requestAnimationFrame(() => modal.classList.add('show')));
}

function closeCommentModal() {
    const modal = document.getElementById('commentModal');
    if (!modal) {
        return;
    }

    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 400);
}

function toggleReplyForm(formId) {
    const form = document.getElementById(formId);
    if (!form) {
        return;
    }

    const shouldShow = !form.classList.contains('show');
    form.classList.toggle('show', shouldShow);

    if (shouldShow) {
        const textarea = form.querySelector('textarea');
        if (textarea) {
            textarea.focus();
        }
    }
}

function toggleEditForm(formId) {
    const form = document.getElementById(formId);
    if (!form) {
        return;
    }

    const shouldShow = !form.classList.contains('show');
    form.classList.toggle('show', shouldShow);

    if (shouldShow) {
        const textarea = form.querySelector('textarea');
        if (textarea) {
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }
    }
}

function toggleReplies(listId, toggleButton) {
    const replyList = document.getElementById(listId);
    if (!replyList || !toggleButton) {
        return;
    }

    const shouldCollapse = !replyList.classList.contains('collapsed');
    replyList.classList.toggle('collapsed', shouldCollapse);
    toggleButton.classList.toggle('collapsed', shouldCollapse);
    toggleButton.setAttribute('aria-expanded', String(!shouldCollapse));
}

function notify(message, options = {}) {
    if (typeof window.showAppToast === 'function') {
        window.showAppToast(message, options);
    }
}

function getCsrfToken() {
    const cookieValue = `; ${document.cookie}`;
    const parts = cookieValue.split('; csrftoken=');
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return '';
}

async function saveCurrentBookToMyBook(button) {
    const isAuthenticated = button.dataset.isAuthenticated === '1';
    const loginUrl = button.dataset.loginUrl || '';
    const saveUrl = button.dataset.saveUrl || '';

    if (!isAuthenticated) {
        notify('Please log in first to save this book.', { tone: 'warning', duration: 2600 });
        if (loginUrl) {
            window.setTimeout(() => {
                window.location.assign(loginUrl);
            }, 900);
        }
        return;
    }

    if (!saveUrl) {
        notify('Could not save this book right now.', { tone: 'error', duration: 2800 });
        return;
    }

    button.disabled = true;
    try {
        const response = await fetch(saveUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
            },
        });

        const payload = await response.json().catch(() => ({}));
        if (!response.ok || payload.ok !== true) {
            throw new Error(payload.error || 'save_failed');
        }

        if (payload.saved) {
            notify('Book added to My Book.', { tone: 'success', duration: 2600 });
        } else {
            notify('This book is already in My Book.', { tone: 'info', duration: 2600 });
        }
    } catch (error) {
        notify('Could not add this book to My Book. Please try again.', {
            tone: 'error',
            duration: 3200,
        });
    } finally {
        button.disabled = false;
    }
}

let currentRating = 0;
function setRating(value, submitAfterSelect = true) {
    currentRating = value;
    const stars = document.querySelectorAll('.rate .rating-star');
    stars.forEach((star, index) => {
        star.classList.toggle('active', index < value);
    });

    const ratingValueInput = document.getElementById('ratingValueInput');
    if (ratingValueInput) {
        ratingValueInput.value = String(value);
    }

    if (submitAfterSelect) {
        const ratingForm = document.getElementById('ratingForm');
        if (ratingForm && ratingValueInput && ratingValueInput.value) {
            ratingForm.submit();
        }
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('commentModal');
    if (modal) {
        modal.addEventListener('click', function (event) {
            if (event.target === modal) {
                closeCommentModal();
            }
        });
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get('show_comments') === '1') {
        openCommentModal();
    }

    const rateBox = document.querySelector('.rate');
    if (rateBox) {
        const initialRating = Number.parseInt(rateBox.dataset.currentRating || '0', 10);
        if (Number.isInteger(initialRating) && initialRating >= 1 && initialRating <= 5) {
            setRating(initialRating, false);
        }
    }

    const addToLibraryBtn = document.getElementById('addToLibraryBtn');
    if (addToLibraryBtn) {
        addToLibraryBtn.addEventListener('click', () => {
            saveCurrentBookToMyBook(addToLibraryBtn);
        });
    }

    const borrowToggleBtn = document.getElementById('borrowToggleBtn');
    const borrowPanel = document.getElementById('borrowPanel');
    if (borrowToggleBtn && borrowPanel) {
        borrowToggleBtn.addEventListener('click', () => {
            const isOpen = borrowPanel.classList.toggle('show');
            borrowToggleBtn.classList.toggle('active', isOpen);
        });
    }
});
/* ── Facebook-style three-dot menu ── */
function toggleMoreMenu(menuId) {
    const menu = document.getElementById(menuId);
    if (!menu) return;

    const isOpen = menu.classList.contains('open');

    // Close every open dropdown first
    document.querySelectorAll('.fb-dropdown.open').forEach(function (el) {
        el.classList.remove('open');
    });

    // If it was closed, open it
    if (!isOpen) {
        menu.classList.add('open');
    }
}

// Close any open dropdown when clicking outside
document.addEventListener('click', function (e) {
    if (!e.target.closest('.fb-more-wrap')) {
        document.querySelectorAll('.fb-dropdown.open').forEach(function (el) {
            el.classList.remove('open');
        });
    }
});