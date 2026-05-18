'use strict';

function setFieldInvalid(field, isInvalid) {
    if (!field) return;
    field.classList.toggle('is-invalid', isInvalid);
    field.setAttribute('aria-invalid', isInvalid ? 'true' : 'false');
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showToast(message, tone) {
    if (typeof window.showAppToast === 'function') {
        window.showAppToast(message, { tone: tone || 'info', duration: 4200 });
    } else {
        alert(message);
    }
}

function submitTicket() {
    const nameInput    = document.getElementById('name');
    const emailInput   = document.getElementById('email');
    const messageInput = document.getElementById('message');
    const orderInput   = document.getElementById('order-id');
    const topicInput   = document.getElementById('topic');

    const nameValue    = (nameInput    ? nameInput.value    : '').trim();
    const emailValue   = (emailInput   ? emailInput.value   : '').trim();
    const messageValue = (messageInput ? messageInput.value : '').trim();

    const nameInvalid    = nameValue.length < 2;
    const emailInvalid   = !isValidEmail(emailValue);
    const messageInvalid = messageValue.length < 10;

    setFieldInvalid(nameInput,    nameInvalid);
    setFieldInvalid(emailInput,   emailInvalid);
    setFieldInvalid(messageInput, messageInvalid);

    if (nameInvalid || emailInvalid || messageInvalid) {
        showToast('Please fill in your name, a valid email, and a detailed message.', 'warning');
        return;
    }

    const ticketId   = `DS-${Math.floor(100000 + Math.random() * 900000)}`;
    const topicValue = topicInput ? topicInput.value : 'General';
    const reply      = `Thanks, ${nameValue}. Your ticket ${ticketId} has been submitted. Topic: ${topicValue}. We'll reply within 2 hours.`;

    showToast(reply, 'success');

    if (messageInput) messageInput.value = '';
    if (orderInput)   orderInput.value   = '';
}

window.submitTicket = submitTicket;

document.addEventListener('DOMContentLoaded', () => {
    ['name', 'email', 'message'].forEach((id) => {
        const field = document.getElementById(id);
        if (field) field.addEventListener('input', () => setFieldInvalid(field, false));
    });
});