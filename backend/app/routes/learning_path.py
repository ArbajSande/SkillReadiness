from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, Dict, Any, List
from app.models.schemas import (
    LearningPathResponse, LearningMilestone, LearningModuleItem,
    LearningProgressUpdateRequest
)
from app.core.security import get_optional_user_id, verify_resource_ownership
from app.core.repository import learning_paths_repo, readiness_repo
from app.services.skill_engine import generate_learning_path_for_gaps, CycleDependencyError

router = APIRouter(prefix="/api/learning-path", tags=["Learning Path & Progress"])

def _calculate_progress(milestones: List[Dict[str, Any]]) -> (int, int, float):
    total = 0
    completed = 0
    for m in milestones:
        for it in m.get("items", []):
            total += 1
            if it.get("completed", False):
                completed += 1
    pct = round((completed / total * 100), 1) if total > 0 else 0.0
    return total, completed, pct

@router.post("/generate", response_model=LearningPathResponse)
async def generate_learning_path(
    target_role: Optional[str] = "Full Stack Developer",
    user_id: str = Depends(get_optional_user_id)
):
    # Lookup latest readiness record strictly for this user
    recent_readiness = await readiness_repo.find_many({"user_id": user_id}, limit=1)
    gap_skills = []
    matched_skills = []
    if recent_readiness:
        r = recent_readiness[0]
        target_role = r.get("target_role", target_role)
        gap_skills = r.get("gap_skills", [])
        matched_skills = r.get("matched_skills", [])

    try:
        milestones_data = generate_learning_path_for_gaps(
            target_role=target_role or "Full Stack Developer",
            gap_skills=gap_skills,
            matched_skills=matched_skills
        )
    except CycleDependencyError as cde:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dependency cycle detected in skill graph: {str(cde)}"
        )

    total_items, completed_items, progress_pct = _calculate_progress(milestones_data)

    record = {
        "user_id": user_id,
        "target_role": target_role,
        "overall_progress_percentage": progress_pct,
        "total_items": total_items,
        "completed_items": completed_items,
        "milestones": milestones_data
    }

    saved = await learning_paths_repo.insert(record)

    milestone_models = []
    for m in milestones_data:
        items = [LearningModuleItem(**it) for it in m["items"]]
        milestone_models.append(LearningMilestone(
            week=m["week"],
            title=m["title"],
            focus_skills=m["focus_skills"],
            items=items
        ))

    return LearningPathResponse(
        id=saved["id"],
        user_id=user_id,
        target_role=target_role,
        overall_progress_percentage=progress_pct,
        total_items=total_items,
        completed_items=completed_items,
        milestones=milestone_models,
        updated_at=saved["created_at"]
    )

@router.get("/current", response_model=Optional[LearningPathResponse])
async def get_current_learning_path(user_id: str = Depends(get_optional_user_id)):
    recent = await learning_paths_repo.find_many({"user_id": user_id}, limit=1)
    if not recent:
        return None
    doc = recent[0]

    milestone_models = []
    for m in doc.get("milestones", []):
        items = [LearningModuleItem(**it) for it in m["items"]]
        milestone_models.append(LearningMilestone(
            week=m["week"],
            title=m["title"],
            focus_skills=m["focus_skills"],
            items=items
        ))

    return LearningPathResponse(
        id=doc["id"],
        user_id=doc.get("user_id", user_id),
        target_role=doc.get("target_role", "Full Stack Developer"),
        overall_progress_percentage=doc.get("overall_progress_percentage", 0.0),
        total_items=doc.get("total_items", 0),
        completed_items=doc.get("completed_items", 0),
        milestones=milestone_models,
        updated_at=doc.get("updated_at", doc.get("created_at", ""))
    )

@router.put("/progress", response_model=LearningPathResponse)
async def update_learning_progress(
    payload: LearningProgressUpdateRequest,
    user_id: str = Depends(get_optional_user_id)
):
    recent = await learning_paths_repo.find_many({"user_id": user_id}, limit=1)
    if not recent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active learning path found for this user. Please generate one first."
        )

    doc = recent[0]
    verify_resource_ownership(doc, user_id, "Learning path")

    milestones = doc.get("milestones", [])
    item_found = False

    for m in milestones:
        for it in m.get("items", []):
            if it.get("id") == payload.item_id:
                it["completed"] = payload.completed
                item_found = True
                break
        if item_found:
            break

    if not item_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning module item '{payload.item_id}' not found in active path."
        )

    total_items, completed_items, progress_pct = _calculate_progress(milestones)

    update_data = {
        "milestones": milestones,
        "total_items": total_items,
        "completed_items": completed_items,
        "overall_progress_percentage": progress_pct
    }

    updated = await learning_paths_repo.update({"id": doc["id"]}, update_data)

    milestone_models = []
    for m in milestones:
        items = [LearningModuleItem(**it) for it in m["items"]]
        milestone_models.append(LearningMilestone(
            week=m["week"],
            title=m["title"],
            focus_skills=m["focus_skills"],
            items=items
        ))

    return LearningPathResponse(
        id=doc["id"],
        user_id=user_id,
        target_role=doc.get("target_role", "Full Stack Developer"),
        overall_progress_percentage=progress_pct,
        total_items=total_items,
        completed_items=completed_items,
        milestones=milestone_models,
        updated_at=updated.get("updated_at", "")
    )
