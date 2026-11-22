"""
DataSip Seed Script
Creates demo user and sample data for testing.
Run with: python -m backend.seed
"""
import sys
import os

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from backend.database import SessionLocal, init_db
from backend import models
from backend.auth import hash_password


def seed():
    """Seed the database with demo user and sample data."""
    print("[*] Starting DataSip seed...")
    init_db()

    db = SessionLocal()
    try:
        # ── Demo User ─────────────────────────────────────────
        existing = db.query(models.User).filter(
            models.User.email == "demo@datasip.ai"
        ).first()

        if existing:
            print("[i] Demo user already exists, skipping user creation.")
            user = existing
        else:
            user = models.User(
                name="Alex Demo",
                email="demo@datasip.ai",
                hashed_password=hash_password("demo1234"),
                education_level="intermediate",
                interests="Python, Machine Learning, Web Development",
                learning_style="practice",
                goal="Become a full-stack ML engineer",
            )
            db.add(user)
            db.flush()
            print("[+] Created demo user: demo@datasip.ai / demo1234")

        # ── Sample Quizzes & Attempts ──────────────────────────
        topics = [
            ("Python Basics", "beginner", 85.0, 5, 4),
            ("Machine Learning", "intermediate", 60.0, 5, 3),
            ("SQL Fundamentals", "beginner", 100.0, 5, 5),
            ("React Hooks", "intermediate", 40.0, 5, 2),
            ("Data Structures", "advanced", 75.0, 4, 3),
            ("Neural Networks", "advanced", 50.0, 4, 2),
            ("Git & Version Control", "beginner", 90.0, 5, 5),
        ]

        base_date = datetime.utcnow() - timedelta(days=len(topics))

        for i, (topic, difficulty, score, total, correct) in enumerate(topics):
            # Create quiz
            quiz = models.Quiz(
                user_id=user.id,
                topic=topic,
                difficulty=difficulty,
                num_questions=total,
                question_type="mcq",
                created_at=base_date + timedelta(days=i),
            )
            db.add(quiz)
            db.flush()

            # Create placeholder questions
            for j in range(total):
                q = models.Question(
                    quiz_id=quiz.id,
                    question_text=f"Sample question {j+1} about {topic}",
                    question_type="mcq",
                    correct_answer="Option A",
                    explanation=f"This is because of the fundamental concepts in {topic}.",
                    order_index=j,
                )
                q.options = ["Option A", "Option B", "Option C", "Option D"]
                db.add(q)

            db.flush()

            # Create attempt
            attempt = models.QuizAttempt(
                quiz_id=quiz.id,
                user_id=user.id,
                score=score,
                total_questions=total,
                correct_count=correct,
                time_taken_seconds=180 + i * 30,
                completed_at=base_date + timedelta(days=i, hours=1),
            )
            attempt.answers = {str(j): "Option A" for j in range(total)}
            db.add(attempt)

            # Create topic progress
            existing_tp = db.query(models.TopicProgress).filter(
                models.TopicProgress.user_id == user.id,
                models.TopicProgress.topic == topic.lower(),
            ).first()

            if not existing_tp:
                tp = models.TopicProgress(
                    user_id=user.id,
                    topic=topic.lower(),
                    attempts=total,
                    correct=correct,
                    last_attempted=base_date + timedelta(days=i),
                )
                db.add(tp)

        print(f"[+] Created {len(topics)} sample quizzes with attempts")

        # ── Sample Chat Session ────────────────────────────────
        existing_session = db.query(models.ChatSession).filter(
            models.ChatSession.user_id == user.id
        ).first()

        if not existing_session:
            session = models.ChatSession(
                user_id=user.id,
                title="What is Machine Learning?",
                created_at=datetime.utcnow() - timedelta(days=2),
                updated_at=datetime.utcnow() - timedelta(days=2),
            )
            db.add(session)
            db.flush()

            messages = [
                ("user", "What is machine learning and how does it work?"),
                ("assistant", "Great question! **Machine Learning** is a subset of artificial intelligence where systems learn from data to improve their performance without being explicitly programmed.\n\nHere's how it works:\n1. **Data Collection** – Gather labeled training data\n2. **Model Training** – Algorithm learns patterns from the data\n3. **Evaluation** – Test accuracy on unseen data\n4. **Prediction** – Use the model to make predictions\n\nThere are three main types:\n- **Supervised Learning** – learns from labeled examples\n- **Unsupervised Learning** – finds patterns in unlabeled data\n- **Reinforcement Learning** – learns through trial and reward\n\nWant me to dive deeper into any of these?"),
                ("user", "Can you explain supervised learning with an example?"),
                ("assistant", "Absolutely! **Supervised Learning** is like teaching a child by showing examples.\n\n**Example: Email Spam Filter**\n\n```python\n# Simplified example\ntraining_data = [\n    ('Buy now! Free offer!', 'spam'),\n    ('Meeting at 3pm tomorrow', 'not spam'),\n    ('Win $1000 instantly', 'spam'),\n]\n\n# Model learns the pattern\nmodel.fit(training_data)\n\n# Predict new email\nresult = model.predict('Click here to claim prize')\n# → 'spam'\n```\n\nThe model learns from thousands of labeled emails and can then classify new, unseen emails. This is called **generalization**!"),
            ]

            for role, content in messages:
                msg = models.ChatMessage(
                    session_id=session.id,
                    role=role,
                    content=content,
                    created_at=datetime.utcnow() - timedelta(days=2),
                )
                db.add(msg)

            print("[+] Created sample chat session")

        db.commit()
        print("\n[OK] Seed completed successfully!")
        print("   Login: demo@datasip.ai / demo1234")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
