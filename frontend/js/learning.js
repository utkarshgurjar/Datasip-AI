/**
 * DataSip Learning Path Interface
 * Render and interact with the AI-generated personalized learning roadmap.
 */

// ── Load & Render Path ─────────────────────────────────────────

async function loadLearningPath() {
  const container = document.getElementById('path-container');
  const emptyState = document.getElementById('path-empty');

  showPathLoading();

  try {
    const path = await api.getLearningPath();
    hidePathLoading();
    renderPath(path);
    renderRecommendations();
  } catch (err) {
    hidePathLoading();
    if (err.message.includes('No learning path')) {
      container.classList.add('hidden');
      if (emptyState) emptyState.classList.remove('hidden');
    } else {
      showToast('Failed to load learning path: ' + err.message, 'error');
    }
  }
}

function showPathLoading() {
  const spinner = document.getElementById('path-loading');
  if (spinner) spinner.classList.remove('hidden');
  const container = document.getElementById('path-container');
  if (container) container.classList.add('hidden');
}

function hidePathLoading() {
  const spinner = document.getElementById('path-loading');
  if (spinner) spinner.classList.add('hidden');
  const container = document.getElementById('path-container');
  if (container) container.classList.remove('hidden');
}

function renderPath(path) {
  // Header info
  const goalEl = document.getElementById('path-goal');
  if (goalEl) goalEl.textContent = path.goal;

  const progressEl = document.getElementById('path-progress-pct');
  if (progressEl) progressEl.textContent = path.progress_percent + '%';

  const progressBar = document.getElementById('path-progress-bar');
  if (progressBar) progressBar.style.width = path.progress_percent + '%';

  const statsEl = document.getElementById('path-stats');
  if (statsEl) {
    statsEl.textContent = `${path.completed_steps} of ${path.total_steps} modules completed`;
  }

  // Steps
  const stepsEl = document.getElementById('steps-container');
  if (!stepsEl) return;

  if (!path.steps.length) {
    stepsEl.innerHTML = '<p class="text-muted">No steps in this path.</p>';
    return;
  }

  stepsEl.innerHTML = path.steps.map((step, i) => {
    const isCompleted = step.completed;
    const isActive = !isCompleted && (i === 0 || path.steps[i - 1]?.completed);
    const statusClass = isCompleted ? 'completed' : isActive ? 'active' : '';

    const resources = (step.resources || []).slice(0, 4);
    const subtopics = step.subtopics || [];

    return `
      <div class="path-step ${statusClass}" id="step-${step.id}">
        <div class="step-indicator">
          ${isCompleted ? '✓' : (i + 1)}
        </div>
        <div class="step-content">
          <div class="step-card">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:0.75rem;">
              <div>
                <div style="font-size:0.75rem;font-weight:700;color:var(--primary);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">
                  Module ${i + 1} · ${escapeHtmlL(step.estimated_time)}
                </div>
                <h3 style="font-size:1.1rem;color:var(--text);">${escapeHtmlL(step.title)}</h3>
              </div>
              <button
                class="btn ${isCompleted ? 'btn-secondary' : 'btn-primary'} btn-sm"
                onclick="toggleStep(${step.id}, ${!isCompleted})"
                id="step-btn-${step.id}"
                style="flex-shrink:0;">
                ${isCompleted ? '↩ Undo' : '✓ Complete'}
              </button>
            </div>

            <p style="color:var(--text-secondary);font-size:0.9rem;margin-bottom:1rem;">${escapeHtmlL(step.description)}</p>

            ${subtopics.length ? `
              <div style="margin-bottom:1rem;">
                <div style="font-size:0.8rem;font-weight:600;color:var(--text);margin-bottom:0.5rem;">📚 Topics Covered</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;">
                  ${subtopics.map(st => `<span class="badge badge-blue">${escapeHtmlL(st)}</span>`).join('')}
                </div>
              </div>
            ` : ''}

            ${resources.length ? `
              <div>
                <div style="font-size:0.8rem;font-weight:600;color:var(--text);margin-bottom:0.5rem;">🔗 Resources</div>
                <div style="display:flex;flex-direction:column;gap:6px;">
                  ${resources.map(r => resourceItem(r)).join('')}
                </div>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function resourceItem(resource) {
  const icons = { video: '🎥', article: '📄', exercise: '💻', book: '📚', course: '🎓' };
  const icon = icons[resource.type] || '🔗';
  const url = resource.url || '#';
  const isExternal = url.startsWith('http');

  return `
    <a href="${escapeHtmlL(url)}" ${isExternal ? 'target="_blank" rel="noopener"' : ''}
       style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--bg-secondary);border-radius:var(--radius);color:var(--text);text-decoration:none;transition:var(--transition);font-size:0.85rem;"
       onmouseover="this.style.background='rgba(14,165,233,0.1)'"
       onmouseout="this.style.background='var(--bg-secondary)'">
      <span>${icon}</span>
      <span style="flex:1;">${escapeHtmlL(resource.title || 'Resource')}</span>
      ${isExternal ? '<span style="color:var(--text-muted);">↗</span>' : ''}
    </a>
  `;
}

// ── Toggle Step Completion ─────────────────────────────────────

async function toggleStep(stepId, completed) {
  const btn = document.getElementById(`step-btn-${stepId}`);
  if (btn) {
    btn.disabled = true;
    btn.textContent = '...';
  }

  try {
    await api.markStep(stepId, { completed });
    showToast(completed ? '✅ Module marked complete!' : 'Module marked incomplete', 'success');
    // Reload path to update visual state
    loadLearningPath();
  } catch (err) {
    showToast('Failed to update step: ' + err.message, 'error');
    if (btn) {
      btn.disabled = false;
      btn.textContent = completed ? '✓ Complete' : '↩ Undo';
    }
  }
}

// ── Generate New Path ──────────────────────────────────────────

async function generatePath() {
  const goalInput = document.getElementById('path-goal-input');
  const goal = goalInput ? goalInput.value.trim() : '';

  const btn = document.getElementById('generate-path-btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Generating with AI...`;
  }

  try {
    const path = await api.generatePath({ goal: goal || undefined, force_regenerate: true });
    document.getElementById('path-empty')?.classList.add('hidden');
    document.getElementById('path-container')?.classList.remove('hidden');
    renderPath(path);
    renderRecommendations();
    showToast('Learning path generated! 🗺️', 'success');
  } catch (err) {
    showToast('Failed to generate path: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '✨ Generate Path';
    }
  }
}

// ── Recommendations ────────────────────────────────────────────

async function renderRecommendations() {
  const container = document.getElementById('recommendations');
  if (!container) return;

  try {
    const recs = await api.getRecommendations();
    container.innerHTML = `
      <div class="card" style="margin-bottom:1rem;">
        <p style="font-weight:600;margin-bottom:0.5rem;">${escapeHtmlL(recs.message)}</p>
        <p style="font-size:0.85rem;color:var(--text-secondary);">Suggested next difficulty: <span class="badge badge-blue">${recs.next_difficulty}</span></p>
      </div>
      ${recs.weak_topics.length ? `
        <div class="card" style="margin-bottom:1rem;">
          <div style="font-size:0.85rem;font-weight:700;color:var(--error);margin-bottom:0.5rem;">⚠️ Topics to Review</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            ${recs.weak_topics.map(t => `<span class="badge badge-red">${escapeHtmlL(t)}</span>`).join('')}
          </div>
        </div>
      ` : ''}
      ${recs.suggested_topics.length ? `
        <div class="card">
          <div style="font-size:0.85rem;font-weight:700;color:var(--primary);margin-bottom:0.5rem;">💡 Suggested Topics</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            ${recs.suggested_topics.map(t => `
              <a href="/quiz.html?topic=${encodeURIComponent(t)}" class="badge badge-blue" style="cursor:pointer;">${escapeHtmlL(t)} →</a>
            `).join('')}
          </div>
        </div>
      ` : ''}
    `;
  } catch (err) {
    container.innerHTML = '<p class="text-muted text-sm">Could not load recommendations.</p>';
  }
}

// ── Helpers ────────────────────────────────────────────────────

function escapeHtmlL(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Init ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;

  loadLearningPath();

  document.getElementById('generate-path-btn')?.addEventListener('click', generatePath);
  document.getElementById('regen-btn')?.addEventListener('click', generatePath);

  // Pre-fill goal from quiz topic URL param
  const params = new URLSearchParams(window.location.search);
  const topicParam = params.get('topic');
  if (topicParam) {
    const goalInput = document.getElementById('path-goal-input');
    if (goalInput) goalInput.value = topicParam;
  }
});
