/**
 * DataSip Auth Utilities
 * Login, register, logout, token/user management, dark mode toggle, toast.
 */

// ── Toast Notifications ────────────────────────────────────────

function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container')
    || (() => {
      const el = document.createElement('div');
      el.id = 'toast-container';
      document.body.appendChild(el);
      return el;
    })();

  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-out');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

window.showToast = showToast;


// ── Dark Mode ──────────────────────────────────────────────────

function initTheme() {
  const saved = localStorage.getItem('datasip_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeToggleIcons(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('datasip_theme', next);
  updateThemeToggleIcons(next);
}

function updateThemeToggleIcons(theme) {
  document.querySelectorAll('.theme-toggle').forEach(btn => {
    btn.textContent = theme === 'dark' ? '☀️' : '🌙';
    btn.title = theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
  });
}

window.toggleTheme = toggleTheme;


// ── Token / User Storage ───────────────────────────────────────

function saveAuth(tokenResponse) {
  localStorage.setItem('datasip_token', tokenResponse.access_token);
  localStorage.setItem('datasip_user', JSON.stringify(tokenResponse.user));
}

function getUser() {
  try {
    const raw = localStorage.getItem('datasip_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function getToken() {
  return localStorage.getItem('datasip_token');
}

function logout() {
  localStorage.removeItem('datasip_token');
  localStorage.removeItem('datasip_user');
  window.location.href = '/login.html';
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = '/login.html';
    return false;
  }
  return true;
}

function redirectIfLoggedIn() {
  if (getToken()) {
    window.location.href = '/dashboard.html';
  }
}

window.saveAuth = saveAuth;
window.getUser  = getUser;
window.getToken = getToken;
window.logout   = logout;
window.requireAuth = requireAuth;
window.redirectIfLoggedIn = redirectIfLoggedIn;


// ── Form Handler Helpers ───────────────────────────────────────

function setButtonLoading(btn, loading, text = '') {
  if (loading) {
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = `<div class="spinner"></div> ${text || 'Loading...'}`;
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.dataset.originalText || text;
    btn.disabled = false;
  }
}

window.setButtonLoading = setButtonLoading;


// ── Login Form ─────────────────────────────────────────────────

function initLoginForm() {
  redirectIfLoggedIn();

  const form = document.getElementById('login-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    setButtonLoading(btn, true, 'Signing in...');

    try {
      const response = await api.login({ email, password });
      saveAuth(response);
      showToast(`Welcome back, ${response.user.name}! 👋`, 'success');
      setTimeout(() => window.location.href = '/dashboard.html', 500);
    } catch (err) {
      showToast(err.message, 'error');
      setButtonLoading(btn, false);
    }
  });
}


// ── Register Form ──────────────────────────────────────────────

function initRegisterForm() {
  redirectIfLoggedIn();

  const form = document.getElementById('register-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    const data = {
      name:            document.getElementById('name').value.trim(),
      email:           document.getElementById('email').value.trim(),
      password:        document.getElementById('password').value,
      education_level: document.getElementById('education_level').value,
      learning_style:  document.getElementById('learning_style').value,
      interests:       document.getElementById('interests').value.trim(),
      goal:            document.getElementById('goal').value.trim(),
    };

    if (data.password !== document.getElementById('confirm_password').value) {
      showToast('Passwords do not match', 'error');
      return;
    }

    setButtonLoading(btn, true, 'Creating account...');

    try {
      const response = await api.register(data);
      saveAuth(response);
      showToast(`Account created! Welcome, ${response.user.name}! 🎉`, 'success');
      setTimeout(() => window.location.href = '/dashboard.html', 500);
    } catch (err) {
      showToast(err.message, 'error');
      setButtonLoading(btn, false);
    }
  });
}


// ── Navbar User Display ────────────────────────────────────────

function initNavbar() {
  const user = getUser();
  const userNameEl = document.getElementById('navbar-user-name');
  if (userNameEl && user) {
    userNameEl.textContent = user.name;
  }

  // Logout button
  document.querySelectorAll('[data-action="logout"]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      logout();
    });
  });

  // Theme toggle
  document.querySelectorAll('.theme-toggle').forEach(btn => {
    btn.addEventListener('click', toggleTheme);
  });
}


// ── Init ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNavbar();
  initLoginForm();
  initRegisterForm();
});
