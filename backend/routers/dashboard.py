"""
DataSip Dashboard Router
Provides aggregated stats for the user's dashboard.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user
from backend.services.personalization_service import calculate_streak

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Return comprehensive dashboard statistics for the current user:
    quiz counts, average score, topic mastery, score trend, and recent activity.
    """
    # ── Quiz attempts ────────────────────────────────────────
    all_attempts = (
        db.query(models.QuizAttempt)
        .filter(models.QuizAttempt.user_id == current_user.id)
        .order_by(models.QuizAttempt.completed_at.desc())
        .all()
    )

    total_quizzes = len(all_attempts)
    avg_score = (
        round(sum(a.score for a in all_attempts) / total_quizzes, 1)
        if total_quizzes > 0
        else 0.0
    )
    best_score = max((a.score for a in all_attempts), default=0.0)

    # ── Streak ────────────────────────────────────────────────
    streak = calculate_streak(current_user.id, db)

    # ── Topic progress ────────────────────────────────────────
    topic_progress = (
        db.query(models.TopicProgress)
        .filter(models.TopicProgress.user_id == current_user.id)
        .all()
    )

    topic_stats = [
        schemas.TopicStat(
            topic=tp.topic,
            accuracy=tp.accuracy,
            attempts=tp.attempts,
            mastery_level=tp.mastery_level,
        )
        for tp in topic_progress
    ]

    # Sort by accuracy descending for strong/weak
    topic_stats_sorted = sorted(topic_stats, key=lambda t: t.accuracy, reverse=True)
    strongest = topic_stats_sorted[:5]
    weakest = sorted(topic_stats, key=lambda t: t.accuracy)[:5]

    # ── Score trend (last 20 attempts, oldest first) ──────────
    recent_for_trend = sorted(all_attempts[:20], key=lambda a: a.completed_at)
    score_trend = [
        schemas.ScoreTrendItem(
            date=a.completed_at.strftime("%Y-%m-%d"),
            score=a.score,
            topic=a.quiz.topic if a.quiz else "Unknown",
        )
        for a in recent_for_trend
    ]

    # ── Recent activity (last 10) ─────────────────────────────
    recent_activity = []
    for attempt in all_attempts[:10]:
        recent_activity.append(
            schemas.QuizHistoryItem(
                attempt_id=attempt.id,
                quiz_id=attempt.quiz_id,
                topic=attempt.quiz.topic if attempt.quiz else "Unknown",
                difficulty=attempt.quiz.difficulty if attempt.quiz else "intermediate",
                score=attempt.score,
                correct_count=attempt.correct_count,
                total_questions=attempt.total_questions,
                completed_at=attempt.completed_at,
            )
        )

    # ── Chat sessions count ───────────────────────────────────
    chat_count = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .count()
    )

    # ── Learning path progress ────────────────────────────────
    path = (
        db.query(models.LearningPath)
        .filter(models.LearningPath.user_id == current_user.id)
        .order_by(models.LearningPath.created_at.desc())
        .first()
    )
    path_progress = 0.0
    if path and path.steps:
        total_steps = len(path.steps)
        done_steps = sum(1 for s in path.steps if s.completed)
        path_progress = round((done_steps / total_steps) * 100, 1)

    return schemas.DashboardStats(
        total_quizzes=total_quizzes,
        average_score=avg_score,
        best_score=best_score,
        current_streak=streak,
        strongest_topics=strongest,
        weakest_topics=weakest,
        score_trend=score_trend,
        topic_mastery=topic_stats_sorted,
        recent_activity=recent_activity,
        total_chat_sessions=chat_count,
        learning_path_progress=path_progress,
    )
