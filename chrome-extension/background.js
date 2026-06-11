// Email Sail Agent — Background Service Worker

chrome.runtime.onInstalled.addListener(() => {
    console.log('⛵ Email Sail Agent extension installed');
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'CLASSIFY_EMAIL') {
        handleClassify(message.data).then(sendResponse);
        return true; // async response
    }
    if (message.type === 'DRAFT_RESPONSE') {
        handleDraft(message.data).then(sendResponse);
        return true;
    }
});

async function handleClassify(data) {
    const { serverUrl } = await chrome.storage.local.get('serverUrl');
    if (!serverUrl) return { error: 'Not connected' };

    try {
        const resp = await fetch(`${serverUrl}/api/emails/${data.messageId}/classify`, {
            method: 'POST',
        });
        return await resp.json();
    } catch (e) {
        return { error: e.message };
    }
}

async function handleDraft(data) {
    const { serverUrl } = await chrome.storage.local.get('serverUrl');
    if (!serverUrl) return { error: 'Not connected' };

    try {
        const resp = await fetch(`${serverUrl}/api/drafts/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return await resp.json();
    } catch (e) {
        return { error: e.message };
    }
}
