const bookCards = Array.from(document.querySelectorAll('.book-card'));
const categorySelect = document.getElementById('category');
const searchInput = document.getElementById('search-input');
const suggestionsContainer = document.getElementById('search-suggestions');
const searchForm = document.querySelector('.search-inline-form');

const BASE_TITLE_SIZE = 20;
const BASE_AUTHOR_SIZE = 14;
const MIN_SCALE = 0.65;
const SCALE_STEP = 0.05;
const SUGGESTION_DEBOUNCE_MS = 180;

let suggestionItems = [];
let activeSuggestionIndex = -1;
let suggestionDebounceTimer = null;
let suggestionAbortController = null;

function filterBooks() {
    if (!categorySelect || !bookCards.length) {
        return;
    }

    const selectedCategory = categorySelect.value;
    bookCards.forEach(card => {
        const cardCategory = card.dataset.category;
        const categoryMatch = selectedCategory === 'all' || cardCategory === selectedCategory;
        card.style.display = categoryMatch ? 'block' : 'none';
    });
}

function autoFitBookCardText() {
    bookCards.forEach(card => {
        const info = card.querySelector('.book-info');
        const title = card.querySelector('.book-title');
        const author = card.querySelector('.book-author');

        if (!info || !title || !author) {
            return;
        }

        card.style.setProperty('--title-font-size', `${BASE_TITLE_SIZE}px`);
        card.style.setProperty('--author-font-size', `${BASE_AUTHOR_SIZE}px`);

        let scale = 1;
        while (info.scrollHeight > info.clientHeight && scale > MIN_SCALE) {
            scale = Math.max(MIN_SCALE, scale - SCALE_STEP);
            card.style.setProperty('--title-font-size', `${(BASE_TITLE_SIZE * scale).toFixed(2)}px`);
            card.style.setProperty('--author-font-size', `${(BASE_AUTHOR_SIZE * scale).toFixed(2)}px`);
        }
    });
}

function clearSuggestionState() {
    suggestionItems = [];
    activeSuggestionIndex = -1;
}

function closeSuggestions() {
    if (!suggestionsContainer) {
        return;
    }

    suggestionsContainer.hidden = true;
    suggestionsContainer.innerHTML = '';
    clearSuggestionState();
}

function setActiveSuggestion(index) {
    if (!suggestionItems.length) {
        activeSuggestionIndex = -1;
        return;
    }

    activeSuggestionIndex = index;
    suggestionItems.forEach((item, itemIndex) => {
        item.classList.toggle('is-active', itemIndex === activeSuggestionIndex);
    });
}

function navigateToSearchResult(url) {
    if (!url) {
        return;
    }
    window.location.assign(url);
}

function submitSearchQuery(queryOverride = null) {
    if (!searchInput || !searchInput.dataset.searchUrl) {
        return;
    }

    const rawQuery = queryOverride === null ? searchInput.value : queryOverride;
    const query = (rawQuery || '').trim();
    if (!query) {
        searchInput.focus();
        return;
    }

    const destination = new URL(searchInput.dataset.searchUrl, window.location.origin);
    destination.searchParams.set('q', query);
    window.location.assign(destination.toString());
}

window.performSearch = function performSearch() {
    submitSearchQuery();
};

function renderSuggestions(suggestions) {
    if (!suggestionsContainer) {
        return;
    }

    suggestionsContainer.innerHTML = '';
    clearSuggestionState();

    if (!Array.isArray(suggestions) || suggestions.length === 0) {
        suggestionsContainer.hidden = true;
        return;
    }

    const fragment = document.createDocumentFragment();
    suggestions.forEach(suggestion => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'search-suggestion-item';
        button.dataset.url = suggestion.url || '';

        const main = document.createElement('span');
        main.className = 'search-suggestion-main';
        main.textContent = suggestion.label || '';

        const sub = document.createElement('span');
        sub.className = 'search-suggestion-sub';
        sub.textContent = suggestion.sub_label || (suggestion.type === 'author' ? 'Author' : 'Book');

        button.appendChild(main);
        button.appendChild(sub);
        fragment.appendChild(button);
    });

    suggestionsContainer.appendChild(fragment);
    suggestionsContainer.hidden = false;
    suggestionItems = Array.from(suggestionsContainer.querySelectorAll('.search-suggestion-item'));
}

async function fetchSuggestions(queryText) {
    if (!searchInput || !searchInput.dataset.suggestionsUrl) {
        return [];
    }

    if (suggestionAbortController) {
        suggestionAbortController.abort();
    }

    suggestionAbortController = new AbortController();
    const params = new URLSearchParams({ q: queryText });
    const requestUrl = `${searchInput.dataset.suggestionsUrl}?${params.toString()}`;

    const response = await fetch(requestUrl, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal: suggestionAbortController.signal,
    });

    if (!response.ok) {
        return [];
    }

    const payload = await response.json();
    if (!payload || !Array.isArray(payload.suggestions)) {
        return [];
    }

    return payload.suggestions;
}

function setupSearchAutocomplete() {
    if (!searchInput || !suggestionsContainer) {
        return;
    }

    suggestionsContainer.addEventListener('mousedown', event => {
        const suggestionItem = event.target.closest('.search-suggestion-item');
        if (!suggestionItem) {
            return;
        }

        event.preventDefault();
        navigateToSearchResult(suggestionItem.dataset.url);
    });

    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim();
        if (suggestionDebounceTimer) {
            clearTimeout(suggestionDebounceTimer);
        }

        if (!query) {
            closeSuggestions();
            return;
        }

        suggestionDebounceTimer = setTimeout(async () => {
            try {
                const snapshot = searchInput.value.trim();
                const suggestions = await fetchSuggestions(snapshot);
                if (snapshot !== searchInput.value.trim()) {
                    return;
                }
                renderSuggestions(suggestions);
            } catch (error) {
                if (error.name !== 'AbortError') {
                    closeSuggestions();
                }
            }
        }, SUGGESTION_DEBOUNCE_MS);
    });

    searchInput.addEventListener('keydown', event => {
        if (!suggestionItems.length) {
            if (event.key === 'Escape') {
                closeSuggestions();
            }
            return;
        }

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            const nextIndex = activeSuggestionIndex + 1 >= suggestionItems.length ? 0 : activeSuggestionIndex + 1;
            setActiveSuggestion(nextIndex);
            return;
        }

        if (event.key === 'ArrowUp') {
            event.preventDefault();
            const nextIndex = activeSuggestionIndex - 1 < 0 ? suggestionItems.length - 1 : activeSuggestionIndex - 1;
            setActiveSuggestion(nextIndex);
            return;
        }

        if (event.key === 'Enter' && activeSuggestionIndex > -1) {
            event.preventDefault();
            navigateToSearchResult(suggestionItems[activeSuggestionIndex].dataset.url);
            return;
        }

        if (event.key === 'Escape') {
            event.preventDefault();
            closeSuggestions();
        }
    });

    document.addEventListener('click', event => {
        if (!suggestionsContainer.hidden && !event.target.closest('.search-container')) {
            closeSuggestions();
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    autoFitBookCardText();
    filterBooks();
    setupSearchAutocomplete();

    if (categorySelect) {
        categorySelect.addEventListener('change', filterBooks);
    }

    if (searchForm && searchInput) {
        searchForm.addEventListener('submit', event => {
            const query = searchInput.value.trim();
            if (!query) {
                event.preventDefault();
                closeSuggestions();
                searchInput.focus();
                return;
            }

            searchInput.value = query;
            closeSuggestions();
        });
    }
});

window.addEventListener('resize', autoFitBookCardText);