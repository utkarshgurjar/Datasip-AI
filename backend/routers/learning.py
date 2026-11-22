"""
DataSip Learning Router
Endpoints: generate/get learning path, mark steps complete, recommendations.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user
from backend.services import gemini_service
from backend.services.personalization_service import get_weak_topics, get_recommendations

router = APIRouter(prefix="/api/learning", tags=["Learning"])


@router.post("/path", response_model=schemas.LearningPathResponse)
def generate_or_get_path(
    request: schemas.LearningPathRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Generate a personalized AI learning path.
    If a path already exists and force_regenerate=False, return existing path.
    """
    # Check for existing path
    if not request.force_regenerate:
        existing_path = (
            db.query(models.LearningPath)
            .filter(models.LearningPath.user_id == current_user.id)
            .order_by(models.LearningPath.created_at.desc())
            .first()
        )
        if existing_path and existing_path.steps:
            return _build_path_response(existing_path)

    # Determine goal
    goal = request.goal or current_user.goal
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a learning goal or update your profile with a goal.",
        )

    # Get weak topics for personalization
    weak_topics = get_weak_topics(current_user.id, db)

    # Call Gemini to generate path
    path_data = gemini_service.generate_learning_path(
        goal=goal,
        level=current_user.education_level,
        weak_topics=weak_topics,
        learning_style=current_user.learning_style,
    )

    if not path_data or "steps" not in path_data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate learning path. Please try again.",
        )

    # Create LearningPath record
    learning_path = models.LearningPath(
        user_id=current_user.id,
        goal=goal,
    )
    db.add(learning_path)
    db.flush()

    # Create LearningStep records
    for step_data in path_data["steps"]:
        step = models.LearningStep(
            path_id=learning_path.id,
            order_index=step_data.get("order", 0),
            title=step_data.get("title", ""),
            description=step_data.get("description", ""),
            estimated_time=step_data.get("estimated_time", ""),
        )
        step.subtopics_list = step_data.get("subtopics", [])
        step.resources_list = step_data.get("resources", [])
        db.add(step)

    db.commit()
    db.refresh(learning_path)
    return _build_path_response(learning_path)


@router.get("/path", response_model=schemas.LearningPathResponse)
def get_path(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the user's current (most recent) learning path."""
    path = (
        db.query(models.LearningPath)
        .filter(models.LearningPath.user_id == current_user.id)
        .order_by(models.LearningPath.created_at.desc())
        .first()
    )

    if not path:
        raise HTTPException(
            status_code=404,
            detail="No learning path found. Generate one first.",
        )

    return _build_path_response(path)


@router.patch("/path/{step_id}", response_model=schemas.LearningStepResponse)
def mark_step_complete(
    step_id: int,
    request: schemas.StepCompleteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a learning step as complete or incomplete."""
    # Verify the step belongs to the current user's path
    step = (
        db.query(models.LearningStep)
        .join(models.LearningPath)
        .filter(
            models.LearningStep.id == step_id,
            models.LearningPath.user_id == current_user.id,
        )
        .first()
    )

    if not step:
        raise HTTPException(status_code=404, detail="Learning step not found")

    step.completed = request.completed
    step.completed_at = datetime.utcnow() if request.completed else None
    db.commit()
    db.refresh(step)

    return schemas.LearningStepResponse(
        id=step.id,
        order_index=step.order_index,
        title=step.title,
        description=step.description,
        subtopics=step.subtopics_list,
        estimated_time=step.estimated_time,
        resources=step.resources_list,
        completed=step.completed,
        completed_at=step.completed_at,
    )


@router.get("/recommendations", response_model=schemas.RecommendationResponse)
def get_recommendations_endpoint(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get personalized study recommendations based on performance."""
    recs = get_recommendations(current_user.id, db)
    return schemas.RecommendationResponse(**recs)


def _build_path_response(path: models.LearningPath) -> schemas.LearningPathResponse:
    """Helper to build a LearningPathResponse from a LearningPath ORM object."""
    steps = sorted(path.steps, key=lambda s: s.order_index)
    total = len(steps)
    completed = sum(1 for s in steps if s.completed)
    progress = round((completed / total) * 100, 1) if total > 0 else 0.0

    step_responses = []
    for s in steps:
        step_responses.append(
            schemas.LearningStepResponse(
                id=s.id,
                order_index=s.order_index,
                title=s.title,
                description=s.description,
                subtopics=s.subtopics_list,
                estimated_time=s.estimated_time,
                resources=s.resources_list,
                completed=s.completed,
                completed_at=s.completed_at,
            )
        )

    return schemas.LearningPathResponse(
        id=path.id,
        goal=path.goal,
        created_at=path.created_at,
        steps=step_responses,
        total_steps=total,
        completed_steps=completed,
        progress_percent=progress,
    )
