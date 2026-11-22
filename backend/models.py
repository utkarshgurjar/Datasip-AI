"""
DataSip ORM Models
All SQLAlchemy table definitions for the application.
"""
import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    """Registered learner with profile information."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Learning profile
    education_level = Column(String(50), default="intermediate")  # beginner/intermediate/advanced
    interests = Column(Text, default="")          # Comma-separated
    learning_style = Column(String(20), default="reading")  # visual/reading/practice
    goal = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete")
    quizzes = relationship("Quiz", back_populates="user", cascade="all, delete")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete")
    topic_progress = relationship("TopicProgress", back_populates="user", cascade="all, delete")
    learning_paths = relationship("LearningPath", back_populates="user", cascade="all, delete")


class ChatSession(Base):
    """A named conversation thread between user and AI tutor."""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete",
                            order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """A single message in a chat session (user or assistant)."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Enum("user", "assistant", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    session = relationship("ChatSession", back_populates="messages")


class Quiz(Base):
    """An AI-generated quiz on a topic."""
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(200), nullable=False)
    difficulty = Column(String(20), default="intermediate")  # beginner/intermediate/advanced
    num_questions = Column(Integer, default=5)
    question_type = Column(String(20), default="mcq")  # mcq/true_false/mixed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete")


class Question(Base):
    """A single question within a quiz."""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="mcq")  # mcq/true_false
    _options = Column("options", Text, default="[]")   # JSON list of strings
    correct_answer = Column(String(500), nullable=False)
    explanation = Column(Text, default="")
    order_index = Column(Integer, default=0)

    # Relationship
    quiz = relationship("Quiz", back_populates="questions")

    @property
    def options(self):
        return json.loads(self._options or "[]")

    @options.setter
    def options(self, value):
        self._options = json.dumps(value)


class QuizAttempt(Base):
    """A user's attempt at completing a quiz."""
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    _answers = Column("answers", Text, default="{}")   # JSON: {question_id: answer}
    score = Column(Float, default=0.0)                 # Percentage 0-100
    total_questions = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    time_taken_seconds = Column(Integer, default=0)
    completed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User", back_populates="quiz_attempts")

    @property
    def answers(self):
        return json.loads(self._answers or "{}")

    @answers.setter
    def answers(self, value):
        self._answers = json.dumps(value)


class TopicProgress(Base):
    """Tracks per-topic performance for a user (used for personalization)."""
    __tablename__ = "topic_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(200), nullable=False, index=True)
    attempts = Column(Integer, default=0)        # Total questions attempted
    correct = Column(Integer, default=0)         # Total correct answers
    last_attempted = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="topic_progress")

    @property
    def accuracy(self) -> float:
        """Returns accuracy as a percentage (0-100)."""
        if self.attempts == 0:
            return 0.0
        return round((self.correct / self.attempts) * 100, 1)

    @property
    def mastery_level(self) -> str:
        """Classify topic as weak / average / strong."""
        acc = self.accuracy
        if acc < 60:
            return "weak"
        elif acc < 80:
            return "average"
        else:
            return "strong"


class LearningPath(Base):
    """An AI-generated personalized learning roadmap."""
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="learning_paths")
    steps = relationship("LearningStep", back_populates="path",
                         cascade="all, delete", order_by="LearningStep.order_index")


class LearningStep(Base):
    """A single module/step within a learning path."""
    __tablename__ = "learning_steps"

    id = Column(Integer, primary_key=True, index=True)
    path_id = Column(Integer, ForeignKey("learning_paths.id"), nullable=False)
    order_index = Column(Integer, default=0)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    subtopics = Column(Text, default="[]")        # JSON list
    estimated_time = Column(String(100), default="")
    resources = Column(Text, default="[]")        # JSON list of {title, url, type}
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationship
    path = relationship("LearningPath", back_populates="steps")

    @property
    def subtopics_list(self):
        return json.loads(self.subtopics or "[]")

    @subtopics_list.setter
    def subtopics_list(self, value):
        self.subtopics = json.dumps(value)

    @property
    def resources_list(self):
        return json.loads(self.resources or "[]")

    @resources_list.setter
    def resources_list(self, value):
        self.resources = json.dumps(value)
