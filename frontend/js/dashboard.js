/**
 * DataSip Dashboard Charts & Stats
 * Fetches dashboard stats and renders Chart.js visualizations.
 */

let scoreChart = null;
let masteryChart = null;

// ── Main Init ──────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const stats = await api.getStats();
    renderStats(stats);
    renderScoreChart(stats.score_trend);
    renderMasteryChart(stats.topic_mastery);
    renderTopics(stats);
    renderRecentActivity(stats.recent_activity);
  } catch (err) {
    showToast('Failed to load dashboard: ' + err.message, 'error');
  }
}

// ── Stats Cards ────────────────────────────────────────────────

function renderStats(stats) {
  setEl('stat-total-quizzes', stats.total_quizzes);
  setEl('stat-avg-score', stats.average_score + '%');
  setEl('stat-best-score', stats.best_score + '%');
  setEl('stat-streak', stats.current_streak + ' days');
  setEl('stat-chat-sessions', stats.total_chat_sessions);
  setEl('stat-path-progress', stats.learning_path_progress + '%');

  // Progress bar for learning path
  const bar = document.getElementById('path-progress-bar');
  if (bar) bar.style.width = stats.learning_path_progress + '%';
}

function setEl(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ── Score Trend Chart ──────────────────────────────────────────

function renderScoreChart(trend) {
  const ctx = document.getElementById('score-chart');
  if (!ctx || !trend.length) return;

  if (scoreChart) scoreChart.destroy();

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#94a3b8' : '#475569';
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';

  scoreChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trend.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }),
      datasets: [{
        label: 'Score %',
        data: trend.map(d => d.score),
        borderColor: '#0ea5e9',
        backgroundColor: 'rgba(14, 165, 233, 0.1)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#0ea5e9',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => `Topic: ${trend[ctx.dataIndex]?.topic || ''}`,
          },
          backgroundColor: isDark ? '#1e293b' : '#fff',
          titleColor: isDark ? '#f1f5f9' : '#0f172a',
          bodyColor: isDark ? '#94a3b8' : '#475569',
          borderColor: isDark ? '#334155' : '#e2e8f0',
          borderWidth: 1,
        },
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          ticks: { color: textColor, callback: v => v + '%' },
          grid: { color: gridColor },
        },
        x: {
          ticks: { color: textColor },
          grid: { display: false },
        },
      },
    },
  });
}

// ── Topic Mastery Bar Chart ────────────────────────────────────

function renderMasteryChart(topicStats) {
  const ctx = document.getElementById('mastery-chart');
  if (!ctx || !topicStats.length) return;

  if (masteryChart) masteryChart.destroy();

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#94a3b8' : '#475569';
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';

  // Show up to 8 topics
  const displayTopics = topicStats.slice(0, 8);

  const colors = displayTopics.map(t => {
    if (t.accuracy >= 80) return 'rgba(16, 185, 129, 0.8)';
    if (t.accuracy >= 60) return 'rgba(245, 158, 11, 0.8)';
    return 'rgba(239, 68, 68, 0.8)';
  });

  masteryChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: displayTopics.map(t => capitalizeWords(t.topic)),
      datasets: [{
        label: 'Accuracy %',
        data: displayTopics.map(t => t.accuracy),
        backgroundColor: colors,
        borderColor: colors.map(c => c.replace('0.8', '1')),
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.raw}% accuracy`,
            afterLabel: (ctx) => `${displayTopics[ctx.dataIndex]?.attempts || 0} questions attempted`,
          },
          backgroundColor: isDark ? '#1e293b' : '#fff',
          titleColor: isDark ? '#f1f5f9' : '#0f172a',
          bodyColor: isDark ? '#94a3b8' : '#475569',
          borderColor: isDark ? '#334155' : '#e2e8f0',
          borderWidth: 1,
        },
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          ticks: { color: textColor, callback: v => v + '%' },
          grid: { color: gridColor },
        },
        x: {
          ticks: { color: textColor, maxRotation: 35 },
          grid: { display: false },
        },
      },
    },
  });
}

// ── Strongest/Weakest Topics ───────────────────────────────────

function renderTopics(stats) {
  const strongEl = document.getElementById('strongest-topics');
  const weakEl   = document.getElementById('weakest-topics');

  if (strongEl) {
    if (!stats.strongest_topics.length) {
      strongEl.innerHTML = '<p class="text-muted text-sm">No data yet</p>';
    } else {
      strongEl.innerHTML = stats.strongest_topics.slice(0, 5).map(t => topicRow(t)).join('');
    }
  }

  if (weakEl) {
    if (!stats.weakest_topics.length) {
      weakEl.innerHTML = '<p class="text-muted text-sm">No data yet</p>';
    } else {
      weakEl.innerHTML = stats.weakest_topics.slice(0, 5).map(t => topicRow(t)).join('');
    }
  }
}

function topicRow(t) {
  const color = t.accuracy >= 80 ? 'var(--success)' : t.accuracy >= 60 ? 'var(--warning)' : 'var(--error)';
  const level = t.mastery_level;
  const badge = level === 'strong' ? 'badge-green' : level === 'average' ? 'badge-yellow' : 'badge-red';

  return `
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem;">
      <div style="flex:1;min-width:0;">
        <div style="font-size:0.875rem;font-weight:600;color:var(--text);truncate;">${capitalizeWords(t.topic)}</div>
        <div class="progress-bar" style="margin-top:4px;height:4px;">
          <div class="progress-fill" style="width:${t.accuracy}%;background:${color};"></div>
        </div>
      </div>
      <span class="badge ${badge}" style="flex-shrink:0;">${Math.round(t.accuracy)}%</span>
    </div>
  `;
}

// ── Recent Activity ────────────────────────────────────────────

function renderRecentActivity(activity) {
  const container = document.getElementById('recent-activity');
  if (!container) return;

  if (!activity.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📊</div>
        <h3>No activity yet</h3>
        <p>Take a quiz to see your progress!</p>
        <a href="/quiz.html" class="btn btn-primary btn-sm mt-4">Take a Quiz</a>
      </div>`;
    return;
  }

  container.innerHTML = activity.map(item => {
    const scoreColor = item.score >= 80 ? 'var(--success)' : item.score >= 60 ? 'var(--warning)' : 'var(--error)';
    const date = new Date(item.completed_at).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });

    return `
      <div style="display:flex;align-items:center;gap:1rem;padding:0.75rem 0;border-bottom:1px solid var(--border);">
        <div style="width:44px;height:44px;border-radius:50%;background:conic-gradient(${scoreColor} ${item.score}%,var(--border) 0%);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
          <div style="width:32px;height:32px;background:var(--surface);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.7rem;font-weight:800;color:${scoreColor};">${Math.round(item.score)}%</div>
        </div>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;color:var(--text);font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtmlD(item.topic)}</div>
          <div style="font-size:0.78rem;color:var(--text-muted);">${item.correct_count}/${item.total_questions} correct · ${capitalizeWords(item.difficulty)}</div>
        </div>
        <div style="font-size:0.78rem;color:var(--text-muted);flex-shrink:0;text-align:right;">${date}</div>
      </div>
    `;
  }).join('');
}

// ── Helpers ────────────────────────────────────────────────────

function capitalizeWords(str) {
  return (str || '').replace(/\b\w/g, l => l.toUpperCase());
}

function escapeHtmlD(text) {
  if (!text) return '';
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Init ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;

  // Show user name
  const user = getUser();
  if (user) {
    const nameEl = document.getElementById('welcome-name');
    if (nameEl) nameEl.textContent = user.name.split(' ')[0];
  }

  loadDashboard();
});
