/**
 * DataSip Chat Interface
 * Handles AI tutor chat: session management, message sending,
 * markdown rendering, typing indicator.
 */

// Uses marked.js and highlight.js from CDN (loaded in chat.html)

let currentSessionId = null;
let isTyping = false;

// ── Markdown Rendering ─────────────────────────────────────────

function renderMarkdown(text) {
  if (typeof marked === 'undefined') return escapeHtml(text);

  // Configure marked
  marked.setOptions({
    highlight: (code, lang) => {
      if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return typeof hljs !== 'undefined' ? hljs.highlightAuto(code).value : code;
    },
    breaks: true,
    gfm: true,
  });

  return marked.parse(text);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}


// ── Message Rendering ──────────────────────────────────────────

function renderMessage(role, content) {
  const user = getUser();
  const isUser = role === 'user';

  const initials = user ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : 'U';

  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = `
    <div class="message-avatar">${isUser ? initials : '🤖'}</div>
    <div class="message-bubble">${isUser ? escapeHtml(content) : renderMarkdown(content)}</div>
  `;
  return div;
}

function appendMessage(role, content) {
  const container = document.getElementById('chat-messages');
  const msgEl = renderMessage(role, content);
  container.appendChild(msgEl);
  container.scrollTop = container.scrollHeight;
  return msgEl;
}


// ── Typing Indicator ───────────────────────────────────────────

function showTyping() {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() {
  const indicator = document.getElementById('typing-indicator');
  if (indicator) indicator.remove();
}


// ── Send Message ───────────────────────────────────────────────

async function sendMessage() {
  if (isTyping) return;

  const input = document.getElementById('chat-input');
  const content = input.value.trim();
  if (!content) return;

  input.value = '';
  input.style.height = 'auto';
  input.disabled = true;

  // Show user message
  appendMessage('user', content);

  // Show typing
  isTyping = true;
  showTyping();

  try {
    const response = await api.sendMessage({
      content,
      session_id: currentSessionId,
    });

    // Update session ID if new session was created
    if (!currentSessionId) {
      currentSessionId = response.session_id;
      // Reload sidebar
      loadSessions();
    }

    hideTyping();
    appendMessage('assistant', response.assistant_message.content);

  } catch (err) {
    hideTyping();
    appendMessage('assistant', `Sorry, I encountered an error: ${err.message}. Please try again.`);
    showToast(err.message, 'error');
  } finally {
    isTyping = false;
    input.disabled = false;
    input.focus();
  }
}


// ── Sessions Sidebar ───────────────────────────────────────────

async function loadSessions() {
  const list = document.getElementById('sessions-list');
  if (!list) return;

  try {
    const sessions = await api.getSessions();
    renderSessionsList(sessions);
  } catch (err) {
    console.error('Failed to load sessions:', err);
  }
}

function renderSessionsList(sessions) {
  const list = document.getElementById('sessions-list');
  if (!sessions.length) {
    list.innerHTML = `
      <div class="empty-state" style="padding: 2rem 1rem;">
        <div style="font-size: 1.5rem">💬</div>
        <p style="font-size:0.8rem">No chats yet</p>
      </div>`;
    return;
  }

  list.innerHTML = sessions.map(s => `
    <div class="chat-session-item ${s.id === currentSessionId ? 'active' : ''}"
         onclick="loadSession(${s.id})"
         id="session-${s.id}">
      <div style="flex:1; min-width:0;">
        <div class="chat-session-title">${escapeHtml(s.title)}</div>
        <div style="font-size:0.75rem; color:var(--text-muted);">${s.message_count} messages</div>
      </div>
      <button class="btn-icon" style="width:28px;height:28px;border:none;background:transparent;padding:0;flex-shrink:0;"
              onclick="deleteSession(event, ${s.id})" title="Delete">🗑️</button>
    </div>
  `).join('');
}

async function loadSession(sessionId) {
  currentSessionId = sessionId;

  // Update active state in sidebar
  document.querySelectorAll('.chat-session-item').forEach(el => {
    el.classList.toggle('active', el.id === `session-${sessionId}`);
  });

  const container = document.getElementById('chat-messages');
  container.innerHTML = '';

  try {
    const session = await api.getSession(sessionId);
    session.messages.forEach(msg => appendMessage(msg.role, msg.content));
  } catch (err) {
    showToast('Failed to load session', 'error');
  }
}

async function deleteSession(event, sessionId) {
  event.stopPropagation();

  if (!confirm('Delete this chat session?')) return;

  try {
    await api.deleteSession(sessionId);
    if (currentSessionId === sessionId) {
      currentSessionId = null;
      document.getElementById('chat-messages').innerHTML = '';
      showWelcomeMessage();
    }
    loadSessions();
    showToast('Session deleted', 'success');
  } catch (err) {
    showToast('Failed to delete session', 'error');
  }
}

function newChat() {
  currentSessionId = null;
  document.getElementById('chat-messages').innerHTML = '';
  document.querySelectorAll('.chat-session-item').forEach(el => el.classList.remove('active'));
  showWelcomeMessage();
  document.getElementById('chat-input').focus();
}

function showWelcomeMessage() {
  const user = getUser();
  const name = user ? user.name.split(' ')[0] : 'there';
  const container = document.getElementById('chat-messages');
  container.innerHTML = `
    <div class="message assistant" style="max-width:100%;">
      <div class="message-avatar">🤖</div>
      <div class="message-bubble">
        <strong>Hi ${escapeHtml(name)}! I'm your DataSip AI Tutor. 👋</strong>
        <p style="color:inherit;margin-top:0.5rem;">I'm here to help you learn anything. Ask me to:</p>
        <ul style="margin-top:0.5rem;">
          <li>Explain a concept at any level</li>
          <li>Give you examples and practice problems</li>
          <li>Help you understand quiz questions</li>
          <li>Guide you through your learning path</li>
        </ul>
        <p style="color:inherit;margin-top:0.5rem;">What would you like to learn today? 🚀</p>
      </div>
    </div>
  `;
}


// ── Input Handling ─────────────────────────────────────────────

function initChatInput() {
  const input = document.getElementById('chat-input');
  if (!input) return;

  // Auto-resize textarea
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 150) + 'px';
  });

  // Ctrl+Enter or Enter (without Shift) to send
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Send button
  const sendBtn = document.getElementById('send-btn');
  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
}


// ── Init ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;

  loadSessions();
  showWelcomeMessage();
  initChatInput();

  // New chat button
  const newChatBtn = document.getElementById('new-chat-btn');
  if (newChatBtn) newChatBtn.addEventListener('click', newChat);
});
