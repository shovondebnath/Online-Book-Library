(function () {
    function getToastStack() {
        let stack = document.getElementById('toastStack');
        if (stack) {
            return stack;
        }

        stack = document.createElement('div');
        stack.id = 'toastStack';
        stack.className = 'toast-stack';
        stack.setAttribute('aria-live', 'polite');
        stack.setAttribute('aria-atomic', 'true');
        document.body.appendChild(stack);
        return stack;
    }

    function hideToast(toast) {
        if (!toast || toast.classList.contains('is-hiding')) {
            return;
        }

        toast.classList.add('is-hiding');
        toast.addEventListener(
            'animationend',
            function () {
                toast.remove();
            },
            { once: true }
        );
    }

    function showAppToast(message, options) {
        const config = options || {};
        const tone = config.tone || 'success';
        const duration = Number(config.duration) || 2800;

        const stack = getToastStack();
        const toast = document.createElement('div');
        toast.className = `app-toast app-toast-${tone}`;
        toast.setAttribute('role', 'status');
        toast.textContent = String(message || 'Done.');

        toast.addEventListener('click', function () {
            hideToast(toast);
        });

        stack.appendChild(toast);
        window.setTimeout(function () {
            hideToast(toast);
        }, duration);

        return toast;
    }

    window.showAppToast = showAppToast;
})();
