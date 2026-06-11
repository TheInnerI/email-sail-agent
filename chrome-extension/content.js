// Email Sail Agent — Content Script (runs on mail.google.com)

(function() {
    'use strict';

    // Add Email Sail buttons to Gmail toolbar
    function injectButtons() {
        // Look for Gmail's toolbar
        const toolbars = document.querySelectorAll('[role="toolbar"]');
        toolbars.forEach(toolbar => {
            if (toolbar.querySelector('.email-sail-btn')) return; // Already injected

            const btn = document.createElement('button');
            btn.className = 'email-sail-btn';
            btn.innerHTML = '⛵ Sail';
            btn.style.cssText = `
                background: #2dd4bf;
                color: #1a2744;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                margin-left: 8px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            `;
            btn.title = 'Classify this email with Email Sail';
            btn.addEventListener('click', handleSailClick);
            toolbar.appendChild(btn);
        });
    }

    async function handleSailClick() {
        // Extract message ID from URL
        const match = window.location.href.match(/\/([a-f0-9]{16,})/);
        if (!match) {
            alert('Email Sail: Open an email first.');
            return;
        }

        const messageId = match[1];

        // Send message to background script
        chrome.runtime.sendMessage(
            { type: 'CLASSIFY_EMAIL', data: { messageId } },
            (response) => {
                if (response?.error) {
                    alert('Email Sail: ' + response.error);
                } else if (response?.category) {
                    // Show classification result
                    showToast(`⛵ Classified as: ${response.category} (${Math.round(response.confidence * 100)}%)`);
                }
            }
        );
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1a2744;
            color: #2dd4bf;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // Watch for Gmail navigation (SPA)
    const observer = new MutationObserver(() => {
        injectButtons();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Initial injection
    setTimeout(injectButtons, 2000);
})();
