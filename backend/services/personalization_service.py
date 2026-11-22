"""
DataSip Personalization Service
Analyzes user performance to classify topics, suggest difficulty,
and generate study recommendations.
"""
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from backend import models


def get_topic_classification(user_id: int, db: Session) -> Dict[str, List[str]]:
    """
    Classify all of a user's topics into weak / average / strong buckets.

    Returns:
        {
          "weak": [...],      # accuracy < 60%
          "average": [...],   # 60% <= accuracy < 80%
          "strong": [...],    # accuracy >= 80%
        }
    """
    progress_records = (
        db.query(models.TopicProgress)
        .filter(models.TopicProgress.user_id == user_id)
        .all()
    )

    result = {"weak": [], "average": [], "strong": []}
    for record in progress_records:
        level = record.mastery_level
        result[level].append(record.topic)

    return result


def get_weak_topics(user_id: int, db: Session) -> List[str]:
    """Return list of topics where the user has accuracy < 60%."""
    classification = get_topic_classification(user_id, db)
    return classification["weak"]


def suggest_next_difficulty(user_id: int, topic: str, db: Session) -> str:
    """
    Suggest the next quiz difficulty for a topic based on recent performance.

    Logic:
    - No history → intermediate
    - accuracy >= 80% → advance one level
    - accuracy < 60% → go back one level
    - else → keep current
    """
    record = (
        db.query(models.TopicProgress)
        .filter(
            models.TopicProgress.user_id == user_id,
            models.TopicProgress.topic == topic.strip().lower(),
        )
        .first()
    )

    if not record or record.attempts == 0:
        return "intermediate"

    acc = record.accuracy
    levels = ["beginner", "intermediate", "advanced"]

    if acc >= 80:
        # Look at the most recent quiz difficulty for this topic
        recent_quiz = (
            db.query(models.Quiz)
            .filter(
                models.Quiz.user_id == user_id,
                models.Quiz.topic.ilike(f"%{topic}%"),
            )
            .order_by(models.Quiz.created_at.desc())
            .first()
        )
        current_level = recent_quiz.difficulty if recent_quiz else "intermediate"
        current_idx = levels.index(current_level) if current_level in levels else 1
        return levels[min(current_idx + 1, 2)]

    elif acc < 60:
        recent_quiz = (
            db.query(models.Quiz)
            .filter(
                models.Quiz.user_id == user_id,
                models.Quiz.topic.ilike(f"%{topic}%"),
            )
            .order_by(models.Quiz.created_at.desc())
            .first()
        )
        current_level = recent_quiz.difficulty if recent_quiz else "intermediate"
        current_idx = levels.index(current_level) if current_level in levels else 1
        return levels[max(current_idx - 1, 0)]

    return "intermediate"


def get_recommendations(user_id: int, db: Session) -> Dict:
    """
    Generate study recommendations based on topic performance.

    Returns:
        Dict with weak_topics, suggested_topics, next_difficulty,
        revision_topics, and a motivational message.
    """
    classification = get_topic_classification(user_id, db)
    weak = classification["weak"]
    average = classification["average"]
    strong = classification["strong"]

    # Topics to revise = weak topics + average topics with many attempts
    revision_topics = weak[:3] if weak else []

    # Suggest branching into new related topics based on strong ones
    suggested = []
    if strong:
        # Suggest deeper dives into strong topics
        suggested = [f"Advanced {t}" for t in strong[:2]]
    if average:
        suggested += average[:2]

    # Overall difficulty suggestion
    all_progress = (
        db.query(models.TopicProgress)
        .filter(models.TopicProgress.user_id == user_id)
        .all()
    )

    if not all_progress:
        next_difficulty = "intermediate"
        message = "Welcome! Start with a quiz to get personalized recommendations."
    else:
        total_acc = sum(p.accuracy for p in all_progress) / len(all_progress)
        if total_acc >= 80:
            next_difficulty = "advanced"
            message = f"🌟 Outstanding! You're mastering these topics. Ready for advanced challenges?"
        elif total_acc >= 60:
            next_difficulty = "intermediate"
            message = f"📈 Great progress! Focus on improving your weaker areas to level up."
        else:
            next_difficulty = "beginner"
            message = f"💪 Keep going! Reviewing the basics will strengthen your foundation."

    return {
        "weak_topics": weak,
        "suggested_topics": suggested,
        "next_difficulty": next_difficulty,
        "revision_topics": revision_topics,
        "message": message,
    }


def calculate_streak(user_id: int, db: Session) -> int:
    """
    Calculate the user's current learning streak in days.
    A streak day = at least one quiz attempt that day.
    """
    from datetime import datetime, timedelta

    attempts = (
        db.query(models.QuizAttempt)
        .filter(models.QuizAttempt.user_id == user_id)
        .order_by(models.QuizAttempt.completed_at.desc())
        .all()
    )

    if not attempts:
        return 0

    # Collect unique dates
    unique_dates = sorted(
        set(a.completed_at.date() for a in attempts),
        reverse=True,
    )

    today = datetime.utcnow().date()
    streak = 0

    for i, date in enumerate(unique_dates):
        expected = today - timedelta(days=i)
        if date == expected:
            streak += 1
        else:
            break

    return streak
