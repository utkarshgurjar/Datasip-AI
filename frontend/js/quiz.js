/**
 * DataSip Quiz Interface
 * One-question-at-a-time flow with timer, progress, result screen.
 */

let currentQuiz = null;
let currentQuestionIndex = 0;
let selectedAnswers = {};   // {questionId: answerText}
let timerInterval = null;
let elapsedSeconds = 0;
let startTime = null;

// ── Generate Quiz ──────────────────────────────────────────────

async function generateQuiz() {
  const topic     = document.getElementById('quiz-topic').value.trim();
  const difficulty = document.getElementById('quiz-difficulty').value;
  const numQ      = parseInt(document.getElementById('quiz-num').value);
  const qType     = document.getElementById('quiz-type').value;

  if (!topic) {
    showToast('Please enter a topic', 'warning');
    document.getElementById('quiz-topic').focus();
    return;
  }

  // Show loading overlay
  showLoadingOverlay('Generating your quiz with AI... ✨');

  try {
    const quiz = await api.generateQuiz({ topic, difficulty, num_questions: numQ, question_type: qType });
    hideLoadingOverlay();
    startQuiz(quiz);
  } catch (err) {
    hideLoadingOverlay();
    showToast(err.message, 'error');
  }
}

function showLoadingOverlay(text = 'Loading...') {
  let overlay = document.getElementById('loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
      <div class="loading-card">
        <div class="spinner spinner-primary" style="width:40px;height:40px;border-width:3px;"></div>
        <p id="loading-text" style="color:var(--text);font-weight:600;">${text}</p>
      </div>`;
    document.body.appendChild(overlay);
  } else {
    document.getElementById('loading-text').textContent = text;
    overlay.classList.remove('hidden');
  }
}

function hideLoadingOverlay() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.add('hidden');
}

// ── Quiz Flow ──────────────────────────────────────────────────

function startQuiz(quiz) {
  currentQuiz = quiz;
  currentQuestionIndex = 0;
  selectedAnswers = {};
  elapsedSeconds = 0;
  startTime = Date.now();

  // Switch to quiz view
  document.getElementById('quiz-setup').classList.add('hidden');
  document.getElementById('quiz-active').classList.remove('hidden');
  document.getElementById('quiz-result').classList.add('hidden');

  // Update header info
  document.getElementById('quiz-topic-display').textContent = quiz.topic;
  document.getElementById('quiz-difficulty-display').textContent = capitalizeFirst(quiz.difficulty);

  // Start timer
  startTimer();

  renderQuestion();
}

function renderQuestion() {
  const q = currentQuiz.questions[currentQuestionIndex];
  const total = currentQuiz.questions.length;
  const progress = ((currentQuestionIndex + 1) / total) * 100;

  // Progress
  document.getElementById('question-progress').style.width = progress + '%';
  document.getElementById('question-counter').textContent = `${currentQuestionIndex + 1} / ${total}`;

  // Question
  document.getElementById('question-number').textContent = `Question ${currentQuestionIndex + 1}`;
  document.getElementById('question-text').textContent = q.question_text;

  // Options
  const letters = ['A', 'B', 'C', 'D', 'E'];
  const container = document.getElementById('options-container');
  const selectedAnswer = selectedAnswers[q.id];

  container.innerHTML = q.options.map((opt, i) => `
    <div class="option-item ${selectedAnswer === opt ? 'selected' : ''}"
         onclick="selectAnswer(${q.id}, '${escapeAttr(opt)}')"
         id="option-${i}">
      <div class="option-letter">${letters[i] || (i + 1)}</div>
      <div class="option-text">${escapeHtmlQ(opt)}</div>
    </div>
  `).join('');

  // Navigation buttons
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const submitBtn = document.getElementById('submit-btn');

  prevBtn.disabled = currentQuestionIndex === 0;

  if (currentQuestionIndex === total - 1) {
    nextBtn.classList.add('hidden');
    submitBtn.classList.remove('hidden');
  } else {
    nextBtn.classList.remove('hidden');
    submitBtn.classList.add('hidden');
  }
}

function selectAnswer(questionId, answer) {
  selectedAnswers[questionId] = answer;

  // Update visual state
  document.querySelectorAll('.option-item').forEach(el => {
    el.classList.remove('selected');
  });

  // Find and select the clicked option
  const q = currentQuiz.questions[currentQuestionIndex];
  const optIdx = q.options.indexOf(answer);
  if (optIdx !== -1) {
    document.getElementById(`option-${optIdx}`)?.classList.add('selected');
  }
}

function prevQuestion() {
  if (currentQuestionIndex > 0) {
    currentQuestionIndex--;
    renderQuestion();
  }
}

function nextQuestion() {
  if (currentQuestionIndex < currentQuiz.questions.length - 1) {
    currentQuestionIndex++;
    renderQuestion();
  }
}

async function submitQuiz() {
  const total = currentQuiz.questions.length;
  const answered = Object.keys(selectedAnswers).length;

  if (answered < total) {
    const unanswered = total - answered;
    if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) return;
  }

  stopTimer();
  showLoadingOverlay('Grading your quiz...');

  // Build answers payload: {questionId: answer}
  const answersPayload = {};
  for (const [qid, ans] of Object.entries(selectedAnswers)) {
    answersPayload[qid] = ans;
  }

  try {
    const result = await api.submitQuiz(currentQuiz.id, {
      answers: answersPayload,
      time_taken_seconds: elapsedSeconds,
    });
    hideLoadingOverlay();
    showResult(result);
  } catch (err) {
    hideLoadingOverlay();
    showToast('Failed to submit quiz: ' + err.message, 'error');
  }
}

// ── Timer ──────────────────────────────────────────────────────

function startTimer() {
  const display = document.getElementById('timer-display');
  timerInterval = setInterval(() => {
    elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
    const mins = Math.floor(elapsedSeconds / 60).toString().padStart(2, '0');
    const secs = (elapsedSeconds % 60).toString().padStart(2, '0');
    if (display) display.textContent = `${mins}:${secs}`;
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
}

// ── Result Screen ──────────────────────────────────────────────

function showResult(result) {
  document.getElementById('quiz-active').classList.add('hidden');
  document.getElementById('quiz-result').classList.remove('hidden');

  const score = result.score;
  const scoreColor = score >= 80 ? 'var(--success)' : score >= 60 ? 'var(--warning)' : 'var(--error)';
  const emoji = score >= 80 ? '🎉' : score >= 60 ? '📈' : '💪';

  // Score ring
  const ring = document.getElementById('score-ring');
  ring.style.background = `conic-gradient(${scoreColor} ${score}%, var(--border) 0%)`;
  ring.innerHTML = `
    <div style="background:var(--surface);width:120px;height:120px;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;">
      <div class="result-score-value" style="color:${scoreColor};">${score}%</div>
      <div style="font-size:1.5rem;">${emoji}</div>
    </div>
  `;

  // Stats
  document.getElementById('result-correct').textContent = `${result.correct_count}/${result.total_questions}`;
  document.getElementById('result-time').textContent = formatTime(result.time_taken_seconds);
  document.getElementById('result-topic').textContent = result.topic;

  // Message
  const messages = {
    great:   'Outstanding performance! You\'ve mastered this topic! 🌟',
    good:    'Good job! A bit more practice and you\'ll ace it! 📚',
    improve: 'Keep studying! Review the explanations below to improve. 💡',
  };
  const msgKey = score >= 80 ? 'great' : score >= 60 ? 'good' : 'improve';
  document.getElementById('result-message').textContent = messages[msgKey];

  // Per-question breakdown
  const breakdown = document.getElementById('questions-breakdown');
  breakdown.innerHTML = result.results.map((r, i) => `
    <div class="card" style="border-left: 4px solid ${r.is_correct ? 'var(--success)' : 'var(--error)'}; margin-bottom:1rem;">
      <div style="display:flex;align-items:flex-start;gap:0.75rem;">
        <span style="font-size:1.2rem;flex-shrink:0;">${r.is_correct ? '✅' : '❌'}</span>
        <div style="flex:1;">
          <p style="font-weight:600;color:var(--text);margin-bottom:0.5rem;">${escapeHtmlQ(r.question_text)}</p>
          ${!r.is_correct ? `<p style="font-size:0.85rem;color:var(--error);margin-bottom:0.25rem;">Your answer: <strong>${escapeHtmlQ(r.your_answer || 'Not answered')}</strong></p>` : ''}
          <p style="font-size:0.85rem;color:var(--success);margin-bottom:0.5rem;">Correct: <strong>${escapeHtmlQ(r.correct_answer)}</strong></p>
          <p style="font-size:0.85rem;color:var(--text-secondary);background:var(--bg-secondary);padding:0.5rem 0.75rem;border-radius:var(--radius);">${escapeHtmlQ(r.explanation)}</p>
        </div>
      </div>
    </div>
  `).join('');
}

function resetToSetup() {
  currentQuiz = null;
  currentQuestionIndex = 0;
  selectedAnswers = {};
  stopTimer();

  document.getElementById('quiz-setup').classList.remove('hidden');
  document.getElementById('quiz-active').classList.add('hidden');
  document.getElementById('quiz-result').classList.add('hidden');
}

// ── Helpers ────────────────────────────────────────────────────

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function capitalizeFirst(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtmlQ(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeAttr(text) {
  return (text || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// ── Load Quiz History ──────────────────────────────────────────

async function loadQuizHistory() {
  const container = document.getElementById('quiz-history');
  if (!container) return;

  try {
    const history = await api.quizHistory();
    if (!history.length) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📝</div><h3>No quizzes yet</h3><p>Generate your first quiz above!</p></div>`;
      return;
    }

    container.innerHTML = history.map(item => {
      const scoreColor = item.score >= 80 ? 'var(--success)' : item.score >= 60 ? 'var(--warning)' : 'var(--error)';
      return `
        <div class="card flex items-center gap-4" style="margin-bottom:0.75rem;">
          <div style="width:52px;height:52px;border-radius:50%;background:conic-gradient(${scoreColor} ${item.score}%,var(--border) 0%);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <div style="width:38px;height:38px;background:var(--surface);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:800;color:${scoreColor};">${Math.round(item.score)}%</div>
          </div>
          <div style="flex:1;">
            <div style="font-weight:600;color:var(--text);">${escapeHtmlQ(item.topic)}</div>
            <div style="font-size:0.8rem;color:var(--text-muted);">${item.correct_count}/${item.total_questions} correct · ${capitalizeFirst(item.difficulty)}</div>
          </div>
          <div style="font-size:0.8rem;color:var(--text-muted);">${new Date(item.completed_at).toLocaleDateString()}</div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<p class="text-muted">Failed to load history.</p>`;
  }
}

// ── Init ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;
  loadQuizHistory();

  document.getElementById('generate-btn')?.addEventListener('click', generateQuiz);
  document.getElementById('prev-btn')?.addEventListener('click', prevQuestion);
  document.getElementById('next-btn')?.addEventListener('click', nextQuestion);
  document.getElementById('submit-btn')?.addEventListener('click', submitQuiz);
  document.getElementById('new-quiz-btn')?.addEventListener('click', resetToSetup);

  // Allow Enter key on topic input
  document.getElementById('quiz-topic')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') generateQuiz();
  });
});
