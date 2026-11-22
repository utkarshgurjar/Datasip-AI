/**
 * DataSip API Client
 * Centralized fetch wrapper that injects JWT token and handles errors.
 */

const API_BASE = '/api';

/**
 * Core fetch wrapper. Automatically adds Authorization header if token exists.
 * @param {string} endpoint  - e.g. '/auth/login'
 * @param {object} options   - standard fetch options
 * @returns {Promise<any>}   - parsed JSON response
 */
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('datasip_token');

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle 204 No Content
  if (response.status === 204) return null;

  // Parse JSON
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data.detail || data.message || `HTTP ${response.status}`;
    // If 401, clear token and redirect to login
    if (response.status === 401) {
      localStorage.removeItem('datasip_token');
      localStorage.removeItem('datasip_user');
      if (!window.location.pathname.includes('login')) {
        window.location.href = '/login.html';
      }
    }
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }

  return data;
}

// ── Convenience methods ────────────────────────────────────────

const api = {
  get:    (endpoint, opts = {}) => apiFetch(endpoint, { method: 'GET', ...opts }),
  post:   (endpoint, body, opts = {}) => apiFetch(endpoint, { method: 'POST', body: JSON.stringify(body), ...opts }),
  put:    (endpoint, body, opts = {}) => apiFetch(endpoint, { method: 'PUT', body: JSON.stringify(body), ...opts }),
  patch:  (endpoint, body, opts = {}) => apiFetch(endpoint, { method: 'PATCH', body: JSON.stringify(body), ...opts }),
  delete: (endpoint, opts = {}) => apiFetch(endpoint, { method: 'DELETE', ...opts }),

  // Auth
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  me:       () => api.get('/auth/me'),
  updateMe: (data) => api.put('/auth/me', data),

  // Chat
  sendMessage: (data) => api.post('/chat/message', data),
  getSessions: () => api.get('/chat/sessions'),
  getSession:  (id) => api.get(`/chat/sessions/${id}`),
  deleteSession: (id) => api.delete(`/chat/sessions/${id}`),

  // Quiz
  generateQuiz: (data) => api.post('/quiz/generate', data),
  getQuiz:      (id) => api.get(`/quiz/${id}`),
  submitQuiz:   (id, data) => api.post(`/quiz/${id}/submit`, data),
  quizHistory:  () => api.get('/quiz/history'),

  // Learning
  generatePath:    (data) => api.post('/learning/path', data),
  getLearningPath: () => api.get('/learning/path'),
  markStep:        (stepId, data) => api.patch(`/learning/path/${stepId}`, data),
  getRecommendations: () => api.get('/learning/recommendations'),

  // Dashboard
  getStats: () => api.get('/dashboard/stats'),
};

window.api = api;
