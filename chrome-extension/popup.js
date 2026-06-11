// Email Sail Agent — Chrome Extension Popup Logic

const DEFAULT_SERVER = 'http://localhost:8090';

// Load saved server URL
document.addEventListener('DOMContentLoaded', async () => {
    const { serverUrl } = await chrome.storage.local.get('serverUrl');
    document.getElementById('server-url').value = serverUrl || DEFAULT_SERVER;
    checkConnection();
});

async function connect() {
    const url = document.getElementById('server-url').value.trim();
    if (!url) { alert('Please enter a server URL'); return; }

    try {
        const resp = await fetch(`${url}/health`, { method: 'GET', signal: AbortSignal.timeout(5000) });
        const data = await resp.json();
        if (data.status === 'healthy') {
            await chrome.storage.local.set({ serverUrl: url, connected: true });
            updateStatus('connected', `Connected to ${url}`);
            document.getElementById('stats-card').style.display = 'block';
            document.getElementById('actions-card').style.display = 'block';
            document.getElementById('auth-card').style.display = 'block';
            loadStats();
        }
    } catch (e) {
        await chrome.storage.local.set({ connected: false });
        updateStatus('disconnected', `Connection failed: ${e.message}`);
        document.getElementById('stats-card').style.display = 'none';
        document.getElementById('actions-card').style.display = 'none';
    }
}

function updateStatus(status, text) {
    const dot = document.querySelector('#connection-status .status-dot');
    const textEl = document.getElementById('status-text');
    dot.className = `status-dot status-${status}`;
    textEl.textContent = text;
}

async function checkConnection() {
    const { connected, serverUrl } = await chrome.storage.local.get(['connected', 'serverUrl']);
    if (connected && serverUrl) {
        try {
            const resp = await fetch(`${serverUrl}/health`, { signal: AbortSignal.timeout(3000) });
            const data = await resp.json();
            if (data.status === 'healthy') {
                updateStatus('connected', `Connected to ${serverUrl}`);
                document.getElementById('stats-card').style.display = 'block';
                document.getElementById('actions-card').style.display = 'block';
                document.getElementById('auth-card').style.display = 'block';
                loadStats();
                return;
            }
        } catch (e) { /* fall through */ }
    }
    updateStatus('disconnected', 'Not connected');
}

async function loadStats() {
    const { serverUrl } = await chrome.storage.local.get('serverUrl');
    try {
        const resp = await fetch(`${serverUrl}/api/emails/list?limit=1`);
        const data = await resp.json();
        document.getElementById('stat-today').textContent = data.count || 0;
    } catch (e) {
        document.getElementById('stat-today').textContent = '—';
    }
    document.getElementById('stat-drafts').textContent = '—';
    document.getElementById('stat-urgent').textContent = '—';
}

function openDashboard() {
    const url = document.getElementById('server-url').value.trim();
    chrome.tabs.create({ url: `${url}/dashboard` });
}

function authorizeGmail() {
    const url = document.getElementById('server-url').value.trim();
    chrome.tabs.create({ url: `${url}/auth/login` });
}

async function classifyCurrent() {
    const { serverUrl } = await chrome.storage.local.get('serverUrl');
    // Get current Gmail tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url?.includes('mail.google.com')) {
        // Extract message ID from URL
        const match = tab.url.match(/\/([a-f0-9]{16,})/);
        if (match) {
            try {
                const resp = await fetch(`${serverUrl}/api/emails/${match[1]}/classify`, { method: 'POST' });
                const data = await resp.json();
                alert(`Classified as: ${data.category} (${Math.round(data.confidence * 100)}%)`);
            } catch (e) { alert('Error: ' + e.message); }
        } else {
            alert('Open an email in Gmail first, then click this button.');
        }
    } else {
        alert('Please open Gmail in the current tab first.');
    }
}

async function draftResponse() {
    const { serverUrl } = await chrome.storage.local.get('serverUrl');
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url?.includes('mail.google.com')) {
        const match = tab.url.match(/\/([a-f0-9]{16,})/);
        if (match) {
            try {
                const resp = await fetch(`${serverUrl}/api/drafts/create`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message_id: match[1], tone: 'professional' }),
                });
                const data = await resp.json();
                if (data.draft_created) {
                    chrome.tabs.create({ url: data.doc_url });
                }
            } catch (e) { alert('Error: ' + e.message); }
        } else {
            alert('Open an email in Gmail first, then click this button.');
        }
    } else {
        alert('Please open Gmail in the current tab first.');
    }
}
