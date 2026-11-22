"""
DataSip Quiz Service
Handles quiz grading, scoring, and per-question result generation.
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend import models
from backend.services import gemini_service


def grade_quiz(
    quiz: models.Quiz,
    answers: Dict[str, str],
    db: Session,
    user: models.User,
) -> Dict[str, Any]:
    """
    Grade a submitted quiz attempt.

    Args:
        quiz: The Quiz ORM object with its questions loaded
        answers: Dict of {str(question_id): answer_text}
        db: Database session
        user: The submitting user

    Returns:
        Dict with score, results per question, and attempt ID
    """
    questions = quiz.questions
    if not questions:
        return {"error": "Quiz has no questions"}

    results = []
    correct_count = 0

    for question in questions:
        q_id_str = str(question.id)
        user_answer = answers.get(q_id_str, "").strip()
        correct = question.correct_answer.strip()
        is_correct = user_answer.lower() == correct.lower()

        if is_correct:
            correct_count += 1

        results.append({
            "question_id": question.id,
            "question_text": question.question_text,
            "your_answer": user_answer,
            "correct_answer": correct,
            "is_correct": is_correct,
            "explanation": question.explanation,
        })

    total = len(questions)
    score = round((correct_count / total) * 100, 1) if total > 0 else 0.0

    return {
        "score": score,
        "correct_count": correct_count,
        "total_questions": total,
        "results": results,
    }


def save_quiz_attempt(
    quiz: models.Quiz,
    user: models.User,
    grade_result: Dict[str, Any],
    answers: Dict[str, str],
    time_taken_seconds: int,
    db: Session,
) -> models.QuizAttempt:
    """
    Persist a quiz attempt and update topic progress.
    """
    attempt = models.QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        score=grade_result["score"],
        total_questions=grade_result["total_questions"],
        correct_count=grade_result["correct_count"],
        time_taken_seconds=time_taken_seconds,
        completed_at=datetime.utcnow(),
    )
    attempt.answers = answers
    db.add(attempt)

    # Update topic progress
    _update_topic_progress(
        user_id=user.id,
        topic=quiz.topic,
        total_questions=grade_result["total_questions"],
        correct=grade_result["correct_count"],
        db=db,
    )

    db.commit()
    db.refresh(attempt)
    return attempt


def _update_topic_progress(
    user_id: int,
    topic: str,
    total_questions: int,
    correct: int,
    db: Session,
) -> None:
    """
    Upsert TopicProgress row for a user/topic pair.
    """
    # Normalize topic name (lowercase, stripped)
    normalized_topic = topic.strip().lower()

    existing = (
        db.query(models.TopicProgress)
        .filter(
            models.TopicProgress.user_id == user_id,
            models.TopicProgress.topic == normalized_topic,
        )
        .first()
    )

    if existing:
        existing.attempts += total_questions
        existing.correct += correct
        existing.last_attempted = datetime.utcnow()
    else:
        progress = models.TopicProgress(
            user_id=user_id,
            topic=normalized_topic,
            attempts=total_questions,
            correct=correct,
            last_attempted=datetime.utcnow(),
        )
        db.add(progress)

    # No commit here — caller commits
