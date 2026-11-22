"""
DataSip Pydantic Schemas
Request/response models for all API endpoints.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─────────────────────────── AUTH ───────────────────────────

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    education_level: str = Field(default="intermediate")
    interests: str = Field(default="")
    learning_style: str = Field(default="reading")
    goal: str = Field(default="")

    @field_validator("education_level")
    @classmethod
    def validate_education(cls, v):
        allowed = {"beginner", "intermediate", "advanced"}
        if v not in allowed:
            raise ValueError(f"education_level must be one of {allowed}")
        return v

    @field_validator("learning_style")
    @classmethod
    def validate_style(cls, v):
        allowed = {"visual", "reading", "practice"}
        if v not in allowed:
            raise ValueError(f"learning_style must be one of {allowed}")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    education_level: Optional[str] = None
    interests: Optional[str] = None
    learning_style: Optional[str] = None
    goal: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    education_level: str
    interests: str
    learning_style: str
    goal: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─────────────────────────── CHAT ───────────────────────────

class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[int] = None   # None = create new session


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatSessionDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[ChatMessageResponse] = []

    model_config = {"from_attributes": True}


class ChatReplyResponse(BaseModel):
    session_id: int
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


# ─────────────────────────── QUIZ ───────────────────────────

class QuizGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200)
    difficulty: str = Field(default="intermediate")
    num_questions: int = Field(default=5, ge=3, le=20)
    question_type: str = Field(default="mcq")

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v):
        allowed = {"beginner", "intermediate", "advanced"}
        if v not in allowed:
            raise ValueError(f"difficulty must be one of {allowed}")
        return v

    @field_validator("question_type")
    @classmethod
    def validate_q_type(cls, v):
        allowed = {"mcq", "true_false", "mixed"}
        if v not in allowed:
            raise ValueError(f"question_type must be one of {allowed}")
        return v


class QuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str
    options: List[str]
    order_index: int

    model_config = {"from_attributes": True}


class QuestionWithAnswer(BaseModel):
    id: int
    question_text: str
    question_type: str
    options: List[str]
    correct_answer: str
    explanation: str
    order_index: int

    model_config = {"from_attributes": True}


class QuizResponse(BaseModel):
    id: int
    topic: str
    difficulty: str
    num_questions: int
    question_type: str
    created_at: datetime
    questions: List[QuestionResponse]

    model_config = {"from_attributes": True}


class QuizSubmitRequest(BaseModel):
    answers: Dict[str, str]   # {question_id: answer_text}
    time_taken_seconds: int = Field(default=0, ge=0)


class QuizResultQuestion(BaseModel):
    question_id: int
    question_text: str
    your_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class QuizSubmitResponse(BaseModel):
    attempt_id: int
    quiz_id: int
    topic: str
    score: float
    correct_count: int
    total_questions: int
    time_taken_seconds: int
    results: List[QuizResultQuestion]
    completed_at: datetime


class QuizHistoryItem(BaseModel):
    attempt_id: int
    quiz_id: int
    topic: str
    difficulty: str
    score: float
    correct_count: int
    total_questions: int
    completed_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────── LEARNING PATH ───────────────────────────

class LearningPathRequest(BaseModel):
    goal: Optional[str] = None   # Uses user's profile goal if None
    force_regenerate: bool = False


class ResourceItem(BaseModel):
    title: str
    url: str = ""
    type: str = "article"  # article/video/exercise


class LearningStepResponse(BaseModel):
    id: int
    order_index: int
    title: str
    description: str
    subtopics: List[str] = []
    estimated_time: str
    resources: List[Any] = []
    completed: bool
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LearningPathResponse(BaseModel):
    id: int
    goal: str
    created_at: datetime
    steps: List[LearningStepResponse]
    total_steps: int
    completed_steps: int
    progress_percent: float

    model_config = {"from_attributes": True}


class StepCompleteRequest(BaseModel):
    completed: bool = True


class RecommendationResponse(BaseModel):
    weak_topics: List[str]
    suggested_topics: List[str]
    next_difficulty: str
    revision_topics: List[str]
    message: str


# ─────────────────────────── DASHBOARD ───────────────────────────

class TopicStat(BaseModel):
    topic: str
    accuracy: float
    attempts: int
    mastery_level: str


class ScoreTrendItem(BaseModel):
    date: str
    score: float
    topic: str


class DashboardStats(BaseModel):
    total_quizzes: int
    average_score: float
    best_score: float
    current_streak: int
    strongest_topics: List[TopicStat]
    weakest_topics: List[TopicStat]
    score_trend: List[ScoreTrendItem]
    topic_mastery: List[TopicStat]
    recent_activity: List[QuizHistoryItem]
    total_chat_sessions: int
    learning_path_progress: float
