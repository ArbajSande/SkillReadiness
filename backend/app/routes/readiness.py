from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, Dict, Any, List
from app.models.schemas import (
    ReadinessCalculateRequest, ReadinessResultResponse, CategoryReadiness,
    ReadinessHistoryItem, ReadinessHistoryResponse
)
from app.core.security import get_optional_user_id, verify_resource_ownership
from app.core.repository import readiness_repo, resumes_repo, assessments_repo
from app.services.skill_engine import calculate_readiness_score

router = APIRouter(prefix="/api/readiness", tags=["Readiness Calculation"])

@router.post("/calculate", response_model=ReadinessResultResponse)
async def calculate_user_readiness(
    payload: ReadinessCalculateRequest,
    user_id: str = Depends(get_optional_user_id)
):
    target_role = payload.target_role or "Full Stack Developer"
    extracted_skills = []

    # 1. Fetch skills from resume with authorization check
    if payload.resume_id:
        resume = await resumes_repo.find_one({"id": payload.resume_id})
        verify_resource_ownership(resume, user_id, "Resume")
        extracted_skills = resume.get("extracted_skills", [])
    else:
        # Fallback to latest resume strictly for this user
        latest_resumes = await resumes_repo.find_many({"user_id": user_id}, limit=1)
        if latest_resumes:
            extracted_skills = latest_resumes[0].get("extracted_skills", [])

    # 2. Fetch assessment scores with authorization check
    demonstrated_skill_scores = None
    assessment_overall_score = None
    is_assessed = False

    if payload.assessment_id:
        assessment = await assessments_repo.find_one({"assessment_id": payload.assessment_id})
        verify_resource_ownership(assessment, user_id, "Assessment")
        if assessment.get("status") == "completed":
            is_assessed = True
            assessment_overall_score = assessment.get("score_percentage", 0.0)
            demonstrated_skill_scores = assessment.get("demonstrated_skill_scores", {})
    else:
        # Check latest completed assessment strictly for this user
        recent_assessments = await assessments_repo.find_many({"user_id": user_id, "status": "completed"}, limit=1)
        if recent_assessments:
            latest = recent_assessments[0]
            is_assessed = True
            assessment_overall_score = latest.get("score_percentage", 0.0)
            demonstrated_skill_scores = latest.get("demonstrated_skill_scores", {})

    # 3. Calculate transparent readiness score (SR-v2.0)
    computed = calculate_readiness_score(
        target_role=target_role,
        extracted_skills=extracted_skills,
        assessment_demonstrated_scores=demonstrated_skill_scores,
        assessment_overall_score=assessment_overall_score,
        is_assessed=is_assessed
    )

    record = {
        "user_id": user_id,
        "target_role": target_role,
        "resume_id": payload.resume_id,
        "assessment_id": payload.assessment_id,
        "formula_version": computed["formula_version"],
        "overall_readiness_score": computed["overall_readiness_score"],
        "readiness_level": computed["readiness_level"],
        "is_assessed": computed["is_assessed"],
        "assessment_coverage_pct": computed["assessment_coverage_pct"],
        "category_breakdown": computed["category_breakdown"],
        "matched_skills": computed["matched_skills"],
        "gap_skills": computed["gap_skills"],
        "critical_core_gaps": computed["critical_core_gaps"],
        "optional_gaps": computed.get("optional_gaps", []),
        "skill_contributions": computed["skill_contributions"],
        "recommendations": computed["recommendations"]
    }

    saved = await readiness_repo.insert(record)

    return ReadinessResultResponse(
        id=saved["id"],
        user_id=user_id,
        target_role=target_role,
        overall_readiness_score=computed["overall_readiness_score"],
        readiness_level=computed["readiness_level"],
        category_breakdown=[CategoryReadiness(**cb) for cb in computed["category_breakdown"]],
        matched_skills=computed["matched_skills"],
        gap_skills=computed["gap_skills"],
        critical_core_gaps=computed["critical_core_gaps"],
        optional_gaps=computed.get("optional_gaps", []),
        recommendations=computed["recommendations"],
        formula_version=computed["formula_version"],
        is_assessed=computed["is_assessed"],
        assessment_coverage_pct=computed["assessment_coverage_pct"],
        skill_contributions=computed["skill_contributions"],
        created_at=saved["created_at"]
    )

@router.get("/latest", response_model=Optional[ReadinessResultResponse])
async def get_latest_readiness(user_id: str = Depends(get_optional_user_id)):
    recent = await readiness_repo.find_many({"user_id": user_id}, limit=1)
    if not recent:
        return None
    doc = recent[0]
    return ReadinessResultResponse(
        id=doc["id"],
        user_id=doc.get("user_id", user_id),
        target_role=doc.get("target_role", "Full Stack Developer"),
        overall_readiness_score=doc.get("overall_readiness_score", 0.0),
        readiness_level=doc.get("readiness_level", "Unknown"),
        category_breakdown=[CategoryReadiness(**cb) for cb in doc.get("category_breakdown", [])],
        matched_skills=doc.get("matched_skills", []),
        gap_skills=doc.get("gap_skills", []),
        critical_core_gaps=doc.get("critical_core_gaps", []),
        optional_gaps=doc.get("optional_gaps", []),
        recommendations=doc.get("recommendations", []),
        formula_version=doc.get("formula_version", "SR-v2.0-baseline"),
        is_assessed=doc.get("is_assessed", False),
        assessment_coverage_pct=doc.get("assessment_coverage_pct", 0.0),
        skill_contributions=doc.get("skill_contributions", []),
        created_at=doc.get("created_at", "")
    )

@router.get("/history", response_model=ReadinessHistoryResponse)
async def get_user_readiness_history(user_id: str = Depends(get_optional_user_id)):
    """
    Returns authentic historical readiness snapshots strictly for the requesting user.
    Protects user data against unauthorized cross-user access.
    """
    snapshots = await readiness_repo.find_many({"user_id": user_id}, limit=50)

    # Sort snapshots chronologically (oldest to newest)
    snapshots.sort(key=lambda s: s.get("created_at", ""))

    items = [
        ReadinessHistoryItem(
            id=s["id"],
            target_role=s.get("target_role", "Full Stack Developer"),
            overall_readiness_score=s.get("overall_readiness_score", 0.0),
            readiness_level=s.get("readiness_level", "Unknown"),
            formula_version=s.get("formula_version", "SR-v2.0-baseline"),
            is_assessed=s.get("is_assessed", False),
            assessment_coverage_pct=s.get("assessment_coverage_pct", 0.0),
            critical_core_gaps=s.get("critical_core_gaps", []),
            optional_gaps=s.get("optional_gaps", []),
            created_at=s.get("created_at", "")
        )
        for s in snapshots
    ]

    return ReadinessHistoryResponse(
        user_id=user_id or "anonymous",
        snapshots_count=len(items),
        snapshots=items
    )
