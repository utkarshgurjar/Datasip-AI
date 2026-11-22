"""
DataSip Chat Router
AI tutor chat endpoints: send message, manage sessions.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user
from backend.services import gemini_service
from backend.services.personalization_service import get_weak_topics

router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _build_gemini_history(messages: List[models.ChatMessage]) -> List[dict]:
    """Convert ChatMessage ORM objects to Gemini API history format."""
    history = []
    for msg in messages:
        role = "user" if msg.role == "user" else "model"
        history.append({"role": role, "parts": [msg.content]})
    return history


@router.post("/message", response_model=schemas.ChatReplyResponse)
def send_message(
    request: schemas.ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Send a message to the AI tutor and get a reply.
    Creates a new session if session_id is not provided.
    """
    # Get or create session
    if request.session_id:
        session = (
            db.query(models.ChatSession)
            .filter(
                models.ChatSession.id == request.session_id,
                models.ChatSession.user_id == current_user.id,
            )
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        # Auto-generate session title from first message
        title = request.content[:50] + ("..." if len(request.content) > 50 else "")
        session = models.ChatSession(
            user_id=current_user.id,
            title=title,
        )
        db.add(session)
        db.flush()  # Get the ID without committing

    # Fetch existing messages for context
    existing_messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at)
        .all()
    )

    # Save user message
    user_msg = models.ChatMessage(
        session_id=session.id,
        role="user",
        content=request.content,
    )
    db.add(user_msg)
    db.flush()

    # Build conversation history for Gemini (all messages + new user message)
    history = _build_gemini_history(existing_messages)
    history.append({"role": "user", "parts": [request.content]})

    # Build user profile dict
    user_profile = {
        "name": current_user.name,
        "education_level": current_user.education_level,
        "learning_style": current_user.learning_style,
        "interests": current_user.interests,
        "goal": current_user.goal,
    }

    # Get weak topics for adaptive context
    weak_topics = get_weak_topics(current_user.id, db)

    # Call Gemini
    reply_text = gemini_service.chat_reply(
        messages=history,
        user_profile=user_profile,
        weak_topics=weak_topics,
    )

    # Save assistant message
    assistant_msg = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply_text,
    )
    db.add(assistant_msg)

    # Update session timestamp
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return schemas.ChatReplyResponse(
        session_id=session.id,
        user_message=schemas.ChatMessageResponse.model_validate(user_msg),
        assistant_message=schemas.ChatMessageResponse.model_validate(assistant_msg),
    )


@router.get("/sessions", response_model=List[schemas.ChatSessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all chat sessions for the current user."""
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .order_by(models.ChatSession.updated_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        msg_count = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.session_id == s.id)
            .count()
        )
        result.append(
            schemas.ChatSessionResponse(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=msg_count,
            )
        )
    return result


@router.get("/sessions/{session_id}", response_model=schemas.ChatSessionDetail)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific chat session with all its messages."""
    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return schemas.ChatSessionDetail(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        messages=[
            schemas.ChatMessageResponse.model_validate(m) for m in session.messages
        ],
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    db.delete(session)
    db.commit()
