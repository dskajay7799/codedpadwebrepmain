/**
 * CodePad — app.js
 * Handles Save, Load, copy-to-clipboard, syntax highlighting, and UI state.
 */

// ── Config ─────────────────────────────────────────────────────────────
// Change this to your deployed backend URL when hosting on Render.
const API_BASE = window.location.origin;  // same origin (Flask serves frontend too)

// ── DOM references ──────────────────────────────────────────────────────
const codeInput       = document.getElementById('code-input');
const langSelect      = document.getElementById('lang-select');
const expirySelect    = document.getElementById('expiry-select');
const saveBtn         = document.getElementById('save-btn');
const saveResult      = document.getElementById('save-result');
const passkeyDisplay  = document.getElementById('passkey-display');
const copyKeyBtn      = document.getElementById('copy-key-btn');
const saveTimestamp   = document.getElementById('save-timestamp');
const saveError       = document.getElementById('save-error');

const passkeyInput    = document.getElementById('passkey-input');
const loadBtn         = document.getElementById('load-btn');
const loadError       = document.getElementById('load-error');
const codeOutput      = document.getElementById('code-output');
const codeDisplay     = document.getElementById('code-display');
const outputLangBadge = document.getElementById('output-lang-badge');
const outputTimestamp = document.getElementById('output-timestamp');
const copyCodeBtn     = document.getElementById('copy-code-btn');
const lineCount       = document.getElementById('line-count');
const loader          = document.getElementById('loader');
const toast           = document.getElementById('toast');

// ── Line counter ────────────────────────────────────────────────────────
codeInput.addEventListener('input', () => {
  const lines = codeInput.value.split('\n').length;
  lineCount.textContent = `${lines} ${lines === 1 ? 'line' : 'lines'}`;
});

// Allow Tab key inside textarea (insert 2 spaces)
codeInput.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    e.preventDefault();
    const start = codeInput.selectionStart;
    const end   = codeInput.selectionEnd;
    codeInput.value = codeInput.value.substring(0, start) + '  ' + codeInput.value.substring(end);
    codeInput.selectionStart = codeInput.selectionEnd = start + 2;
  }
});

// ── Save Code ───────────────────────────────────────────────────────────
saveBtn.addEventListener('click', async () => {
  const code   = codeInput.value.trim();
  const lang   = langSelect.value;
  const expiry = expirySelect.value;

  // Validate
  if (!code) {
    showError(saveError, 'Please enter some code before saving.');
    return;
  }

  // UI: loading state
  setLoading(saveBtn, true);
  hide(saveResult);
  hide(saveError);

  try {
    const response = await fetch(`${API_BASE}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, language: lang, expiry })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to save code.');
    }

    // Show passkey
    passkeyDisplay.textContent = data.passkey;
    saveTimestamp.textContent  = `Saved at ${formatTime(new Date())}`;
    show(saveResult);
    showToast('Code saved! ✓');

  } catch (err) {
    showError(saveError, err.message);
  } finally {
    setLoading(saveBtn, false);
  }
});

// ── Copy passkey ────────────────────────────────────────────────────────
copyKeyBtn.addEventListener('click', () => {
  copyToClipboard(passkeyDisplay.textContent, 'Passkey copied!');
});

// ── Load Code ───────────────────────────────────────────────────────────
loadBtn.addEventListener('click', () => loadCode());

// Also trigger load on Enter key in passkey input
passkeyInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') loadCode();
});

async function loadCode() {
  const passkey = passkeyInput.value.trim();

  if (!passkey) {
    showError(loadError, 'Please enter a passkey.');
    return;
  }

  // UI: loading state
  setLoading(loadBtn, true);
  hide(loadError);
  hide(codeOutput);
  show(loader);

  try {
    const response = await fetch(`${API_BASE}/load/${encodeURIComponent(passkey)}`);
    const data     = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Code not found. Check your passkey.');
    }

    // Populate code display
    const lang = data.language || 'plaintext';
    codeDisplay.textContent  = data.code;
    outputLangBadge.textContent = lang;
    outputTimestamp.textContent = data.saved_at
      ? `Saved ${formatTime(new Date(data.saved_at))}`
      : '';

    // Apply syntax highlighting
    codeDisplay.className = `hljs language-${lang}`;
    hljs.highlightElement(codeDisplay);

    hide(loader);
    show(codeOutput);
    showToast('Code loaded! ✓');

  } catch (err) {
    hide(loader);
    showError(loadError, err.message);
  } finally {
    setLoading(loadBtn, false);
  }
}

// ── Copy loaded code ────────────────────────────────────────────────────
copyCodeBtn.addEventListener('click', () => {
  copyToClipboard(codeDisplay.textContent, 'Code copied!');
});

// ── Helpers ─────────────────────────────────────────────────────────────

/**
 * Copy text to clipboard and show a toast message.
 */
function copyToClipboard(text, message = 'Copied!') {
  navigator.clipboard.writeText(text).then(() => {
    showToast(message);
  }).catch(() => {
    // Fallback for older browsers
    const el = document.createElement('textarea');
    el.value = text;
    el.style.position = 'fixed';
    el.style.opacity  = '0';
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    showToast(message);
  });
}

/**
 * Show a temporary toast notification.
 */
let toastTimer = null;
function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  toast.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove('show');
  }, 2200);
}

/**
 * Display an error message in the given error box.
 */
function showError(el, message) {
  el.textContent = `⚠ ${message}`;
  show(el);
}

/**
 * Toggle button loading state.
 */
function setLoading(btn, isLoading) {
  btn.disabled = isLoading;
  btn.classList.toggle('loading', isLoading);
}

function show(el) { el.classList.remove('hidden'); }
function hide(el) { el.classList.add('hidden'); }

/**
 * Format a Date object into a human-readable string.
 */
function formatTime(date) {
  return date.toLocaleString(undefined, {
    month:  'short',
    day:    'numeric',
    hour:   '2-digit',
    minute: '2-digit'
  });
}

// ── Auto-load from URL hash ─────────────────────────────────────────────
// Supports links like https://yoursite.com/#abc123
window.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash.slice(1); // strip '#'
  if (hash) {
    passkeyInput.value = hash;
    loadCode();
    // Scroll to load panel
    document.getElementById('load-panel').scrollIntoView({ behavior: 'smooth' });
  }
});