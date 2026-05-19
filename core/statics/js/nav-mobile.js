document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('hamburger-toggle');
    const mobileNav = document.getElementById('mobile-nav');
    const mobileLinks = document.getElementById('mobile-nav-links');
    const navLinks = document.querySelector('.nav-links');

    if (!toggle || !mobileNav || !mobileLinks || !navLinks) {
        return;
    }

    if (!mobileLinks.hasChildNodes()) {
        const clonedLinks = navLinks.cloneNode(true);
        clonedLinks.classList.remove('nav-links');
        clonedLinks.classList.add('mobile-nav-list');
        mobileLinks.appendChild(clonedLinks);
    }

    const closeMenu = () => {
        mobileNav.classList.remove('is-open');
        mobileNav.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
    };

    const openMenu = () => {
        mobileNav.hidden = false;
        requestAnimationFrame(() => {
            mobileNav.classList.add('is-open');
        });
        toggle.setAttribute('aria-expanded', 'true');
    };

    toggle.addEventListener('click', (event) => {
        event.stopPropagation();
        if (mobileNav.hidden) {
            openMenu();
        } else {
            closeMenu();
        }
    });

    document.addEventListener('click', (event) => {
        if (mobileNav.hidden) {
            return;
        }
        if (!mobileNav.contains(event.target) && !toggle.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });

    mobileNav.addEventListener('click', (event) => {
        const target = event.target.closest('a, button');
        if (target) {
            closeMenu();
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 460) {
            closeMenu();
        }
    });
});
