(function () {
    const menu = document.getElementById('profile-menu');
    const trigger = document.getElementById('avatar-trigger');
    const dropdown = document.getElementById('profile-dropdown');
    const note = document.getElementById('profile-note');
    const myBooksTrigger = document.getElementById('my-books-trigger');
    const myBooksModal = document.getElementById('myBooksModal');
    const myBooksModalClose = document.getElementById('myBooksModalClose');
    const myBooksList = document.getElementById('myBooksList');
    const myBooksStatus = document.getElementById('myBooksStatus');

    if (!menu || !trigger || !dropdown) {
        return;
    }

    function openMenu() {
        dropdown.hidden = false;
        menu.classList.add('open');
        trigger.setAttribute('aria-expanded', 'true');
    }

    function closeMenu() {
        dropdown.hidden = true;
        menu.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
    }

    function toggleMenu() {
        if (dropdown.hidden) {
            openMenu();
        } else {
            closeMenu();
        }
    }

    function openMyBooksModal() {
        if (!myBooksModal) {
            return;
        }

        myBooksModal.style.display = 'flex';
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                myBooksModal.classList.add('show');
                myBooksModal.setAttribute('aria-hidden', 'false');
            });
        });
    }

    function closeMyBooksModal() {
        if (!myBooksModal) {
            return;
        }

        myBooksModal.classList.remove('show');
        myBooksModal.setAttribute('aria-hidden', 'true');
        window.setTimeout(function () {
            myBooksModal.style.display = 'none';
        }, 260);
    }

    function setMyBooksStatus(text, isError) {
        if (!myBooksStatus) {
            return;
        }

        myBooksStatus.hidden = false;
        myBooksStatus.textContent = text;
        myBooksStatus.classList.toggle('is-error', Boolean(isError));
    }

    function hideMyBooksStatus() {
        if (!myBooksStatus) {
            return;
        }

        myBooksStatus.hidden = true;
        myBooksStatus.classList.remove('is-error');
    }

    function notify(message, options) {
        if (typeof window.showAppToast === 'function') {
            window.showAppToast(message, options || {});
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

    function setRemoveButtonConfirmState(removeButton, cancelButton, confirming) {
        if (!removeButton) {
            return;
        }

        if (confirming) {
            removeButton.dataset.confirming = '1';
            removeButton.textContent = 'Confirm Remove';
            removeButton.classList.add('is-confirming');
            if (cancelButton) {
                cancelButton.hidden = false;
                cancelButton.classList.add('is-visible');
            }
            return;
        }

        removeButton.dataset.confirming = '0';
        removeButton.textContent = 'Remove';
        removeButton.classList.remove('is-confirming');
        if (cancelButton) {
            cancelButton.classList.remove('is-visible');
            cancelButton.hidden = true;
        }
    }

    async function removeMyBook(item, removeButton, cancelButton, removeUrl) {
        if (!removeUrl) {
            notify('Could not remove this book right now.', { tone: 'error', duration: 3000 });
            return;
        }

        removeButton.disabled = true;
        if (cancelButton) {
            cancelButton.disabled = true;
        }
        try {
            const response = await fetch(removeUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                },
            });

            const payload = await response.json().catch(function () {
                return {};
            });

            if (!response.ok || payload.ok !== true) {
                throw new Error(payload.error || 'remove_failed');
            }

            if (payload.removed) {
                item.remove();
                notify('Book removed from My Book.', { tone: 'success', duration: 2600 });

                if (!myBooksList || myBooksList.children.length === 0) {
                    setMyBooksStatus('No books in My Book yet. Add a book from an openbook page first.', false);
                }
                return;
            }

            notify('This book was already removed.', { tone: 'info', duration: 2600 });
            item.remove();
            if (!myBooksList || myBooksList.children.length === 0) {
                setMyBooksStatus('No books in My Book yet. Add a book from an openbook page first.', false);
            }
        } catch (error) {
            notify('Could not remove this book. Please try again.', { tone: 'error', duration: 3200 });
            setRemoveButtonConfirmState(removeButton, cancelButton, false);
        } finally {
            removeButton.disabled = false;
            if (cancelButton) {
                cancelButton.disabled = false;
            }
        }
    }

    function renderMyBooks(books) {
        if (!myBooksList) {
            return;
        }

        myBooksList.innerHTML = '';

        if (!Array.isArray(books) || books.length === 0) {
            setMyBooksStatus('No books in My Book yet. Add a book from an openbook page first.', false);
            return;
        }

        hideMyBooksStatus();

        books.forEach(function (book) {
            const item = document.createElement('div');
            item.className = 'library-book-item';

            const cover = document.createElement('img');
            cover.className = 'library-book-cover';
            cover.alt = `${book.title || 'Book'} cover`;
            cover.src = book.cover_image_url || `https://picsum.photos/seed/book${book.book_id || 'x'}/300/400`;

            const meta = document.createElement('div');
            meta.className = 'library-book-meta';

            const title = document.createElement('p');
            title.className = 'library-book-title';
            title.textContent = book.title || 'Untitled';

            const author = document.createElement('p');
            author.className = 'library-book-author';
            author.textContent = book.author ? `by ${book.author}` : 'Unknown author';

            const actions = document.createElement('div');
            actions.className = 'library-book-actions';

            const openLink = document.createElement('a');
            openLink.className = 'library-book-open-btn';
            openLink.href = book.openbook_url || '#';
            openLink.textContent = 'Open';

            const removeButton = document.createElement('button');
            removeButton.type = 'button';
            removeButton.className = 'library-book-remove-btn';
            removeButton.textContent = 'Remove';

            const cancelButton = document.createElement('button');
            cancelButton.type = 'button';
            cancelButton.className = 'library-book-cancel-btn';
            cancelButton.textContent = 'Cancel';
            cancelButton.hidden = true;

            let removeConfirmTimer = null;

            function resetRemoveConfirmState() {
                if (removeConfirmTimer) {
                    window.clearTimeout(removeConfirmTimer);
                    removeConfirmTimer = null;
                }
                setRemoveButtonConfirmState(removeButton, cancelButton, false);
            }

            setRemoveButtonConfirmState(removeButton, cancelButton, false);

            cancelButton.addEventListener('click', function () {
                resetRemoveConfirmState();
            });

            removeButton.addEventListener('click', function () {
                if (removeButton.dataset.confirming !== '1') {
                    setRemoveButtonConfirmState(removeButton, cancelButton, true);
                    removeConfirmTimer = window.setTimeout(function () {
                        if (removeButton.dataset.confirming === '1') {
                            resetRemoveConfirmState();
                        }
                    }, 4000);
                    return;
                }

                resetRemoveConfirmState();
                removeMyBook(item, removeButton, cancelButton, book.remove_url || '');
            });

            meta.appendChild(title);
            meta.appendChild(author);
            actions.appendChild(openLink);
            actions.appendChild(removeButton);
            actions.appendChild(cancelButton);
            item.appendChild(cover);
            item.appendChild(meta);
            item.appendChild(actions);
            myBooksList.appendChild(item);
        });
    }

    async function loadMyBooks() {
        if (!myBooksTrigger) {
            return;
        }

        const listUrl = myBooksTrigger.getAttribute('data-list-url');
        if (!listUrl) {
            setMyBooksStatus('Could not load My Book right now.', true);
            return;
        }

        setMyBooksStatus('Loading your books...', false);
        if (myBooksList) {
            myBooksList.innerHTML = '';
        }

        try {
            const response = await fetch(listUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            });

            const payload = await response.json().catch(function () {
                return {};
            });

            if (!response.ok || payload.ok !== true) {
                throw new Error('my_books_unavailable');
            }

            renderMyBooks(payload.books || []);
        } catch (error) {
            setMyBooksStatus('Could not load My Book. Please try again.', true);
            if (typeof window.showAppToast === 'function') {
                window.showAppToast('Could not load My Book right now.', {
                    tone: 'error',
                    duration: 3000,
                });
            }
        }
    }

    trigger.addEventListener('click', function (event) {
        event.stopPropagation();
        toggleMenu();
    });

    dropdown.addEventListener('click', function (event) {
        event.stopPropagation();
    });

    document.addEventListener('click', closeMenu);

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            if (myBooksModal && myBooksModal.classList.contains('show')) {
                closeMyBooksModal();
                return;
            }

            closeMenu();
        }
    });

    if (myBooksTrigger && myBooksModal) {
        myBooksTrigger.addEventListener('click', function (event) {
            event.preventDefault();
            closeMenu();
            openMyBooksModal();
            loadMyBooks();
        });
    }

    if (myBooksModalClose) {
        myBooksModalClose.addEventListener('click', function () {
            closeMyBooksModal();
        });
    }

    if (myBooksModal) {
        myBooksModal.addEventListener('click', function (event) {
            if (event.target === myBooksModal) {
                closeMyBooksModal();
            }
        });
    }

    dropdown.querySelectorAll('[data-profile-action]').forEach(function (button) {
        button.addEventListener('click', function () {
            const action = button.getAttribute('data-profile-action');
            if (!note) {
                return;
            }

            if (action === 'transactions') {
                note.textContent = 'Transactions page will be available soon.';
                return;
            }

            if (action === 'credit') {
                note.textContent = 'Credit details page will be available soon.';
            }
        });
    });
})();
