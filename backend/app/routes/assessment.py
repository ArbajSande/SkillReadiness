import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, Dict, Any, List
from app.models.schemas import (
    AssessmentGenerateRequest, AssessmentSessionResponse, AssessmentQuestion,
    AssessmentSubmitRequest, AssessmentResultResponse, QuestionResult,
    AdaptiveStartRequest, AdaptiveStartResponse, AdaptiveNextRequest, AdaptiveNextResponse,
    AdaptiveQuestionFeedback
)
from app.core.security import get_optional_user_id, verify_resource_ownership
from app.core.repository import assessments_repo
from app.services.skill_engine import (
    generate_assessment_for_role, grade_assessment, select_next_adaptive_question
)

router = APIRouter(prefix="/api/assessment", tags=["Assessment"])

# ---------------------------------------------------------------------------
# INTERACTIVE ADAPTIVE ASSESSMENT WORKFLOW (ADAPT-v1.0-baseline)
# ---------------------------------------------------------------------------

@router.post("/adaptive/start", response_model=AdaptiveStartResponse)
async def start_adaptive_assessment(
    payload: AdaptiveStartRequest,
    user_id: str = Depends(get_optional_user_id)
):
    """
    Initializes an interactive, one-question-at-a-time adaptive assessment session.
    Picks the initial question deterministically at 'Intermediate' baseline difficulty.
    Sensitive server metadata (correct answer index and explanation) are kept on the server.
    """
    max_q = max(3, min(payload.max_questions, 10))
    initial_q = select_next_adaptive_question(
        target_role=payload.target_role,
        answered_questions=[],
        user_skills=payload.skills,
        session_max_questions=max_q
    )

    if not initial_q:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to initialize assessment: No suitable questions found for role '{payload.target_role}'."
        )

    assessment_id = f"asm_adapt_{uuid.uuid4().hex[:12]}"
    record = {
        "assessment_id": assessment_id,
        "user_id": user_id,
        "target_role": payload.target_role,
        "max_questions": max_q,
        "answered_questions": [],
        "current_question_server": initial_q,
        "status": "in_progress",
        "policy_version": "ADAPT-v1.0-baseline"
    }

    saved = await assessments_repo.insert(record)

    # Client-facing question model without correct_option or explanation
    client_q = AssessmentQuestion(
        id=initial_q["id"],
        question=initial_q["question"],
        options=initial_q["options"],
        skill=initial_q["skill"],
        difficulty=initial_q["difficulty"]
    )

    return AdaptiveStartResponse(
        assessment_id=assessment_id,
        target_role=payload.target_role,
        question_number=1,
        total_questions=max_q,
        question=client_q,
        is_completed=False,
        policy_version="ADAPT-v1.0-baseline",
        created_at=saved["created_at"]
    )

@router.post("/adaptive/next", response_model=AdaptiveNextResponse)
async def submit_adaptive_answer_and_get_next(
    payload: AdaptiveNextRequest,
    user_id: str = Depends(get_optional_user_id)
):
    """
    Grades the submitted answer server-side, generates immediate feedback,
    and uses the ADAPT-v1.0-baseline policy to select the next adaptive question
    (stepping up difficulty on correct, stepping down on incorrect).
    """
    assessment = await assessments_repo.find_one({"assessment_id": payload.assessment_id})
    verify_resource_ownership(assessment, user_id, "Adaptive assessment")

    if assessment.get("status") == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment has already been completed."
        )

    current_q = assessment.get("current_question_server")
    if not current_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment session has no active question."
        )

    # Client question tampering prevention
    if payload.question_id != current_q["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question mismatch. Expected question '{current_q['id']}', received '{payload.question_id}'."
        )

    if payload.selected_option < 0 or payload.selected_option >= len(current_q["options"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected option is outside the valid range."
        )

    # Server-Side Grading
    is_correct = (payload.selected_option == current_q["correct_option"])
    feedback = AdaptiveQuestionFeedback(
        question_id=current_q["id"],
        question=current_q["question"],
        skill=current_q["skill"],
        selected_option=payload.selected_option,
        correct_option=current_q["correct_option"],
        is_correct=is_correct,
        explanation=current_q.get("explanation", ""),
        difficulty=current_q.get("difficulty", "Intermediate")
    )

    answered_questions: List[Dict[str, Any]] = assessment.get("answered_questions", [])
    answered_questions.append(feedback.model_dump())

    max_q = assessment.get("max_questions", 5)
    target_role = assessment.get("target_role", "Full Stack Developer")

    # Select next adaptive question using ADAPT-v1.0-baseline
    next_q = select_next_adaptive_question(
        target_role=target_role,
        answered_questions=answered_questions,
        session_max_questions=max_q
    )

    # Check if session is completed
    if next_q is None or len(answered_questions) >= max_q:
        # Finalize and compile scorecard
        correct_count = sum(1 for a in answered_questions if a["is_correct"])
        total_answered = len(answered_questions)
        score_pct = round((correct_count / total_answered * 100), 1) if total_answered > 0 else 0.0

        skill_counts: Dict[str, Dict[str, int]] = {}
        category_counts: Dict[str, Dict[str, int]] = {}

        for a in answered_questions:
            sk = a["skill"]
            cat = a.get("category", "Technical")
            if sk not in skill_counts:
                skill_counts[sk] = {"total": 0, "correct": 0}
            skill_counts[sk]["total"] += 1
            if a["is_correct"]:
                skill_counts[sk]["correct"] += 1

            if cat not in category_counts:
                category_counts[cat] = {"total": 0, "correct": 0}
            category_counts[cat]["total"] += 1
            if a["is_correct"]:
                category_counts[cat]["correct"] += 1

        demonstrated_skill_scores = {}
        demonstrated_levels = {}
        for sk, stats in skill_counts.items():
            pct = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
            demonstrated_skill_scores[sk] = round(pct, 2)
            if pct >= 0.8:
                demonstrated_levels[sk] = "Advanced"
            elif pct >= 0.5:
                demonstrated_levels[sk] = "Intermediate"
            else:
                demonstrated_levels[sk] = "Demonstrated Gap"

        category_scores = {
            cat: round((stats["correct"] / stats["total"] * 100), 1)
            for cat, stats in category_counts.items() if stats["total"] > 0
        }

        question_results = [
            QuestionResult(
                question_id=a["question_id"],
                question=a["question"],
                skill=a["skill"],
                selected_option=a["selected_option"],
                correct_option=a["correct_option"],
                is_correct=a["is_correct"],
                explanation=a["explanation"],
                difficulty=a["difficulty"]
            )
            for a in answered_questions
        ]

        update_payload = {
            "status": "completed",
            "answered_questions": answered_questions,
            "current_question_server": None,
            "score_percentage": score_pct,
            "correct_answers": correct_count,
            "total_questions": total_answered,
            "category_scores": category_scores,
            "demonstrated_skill_scores": demonstrated_skill_scores,
            "demonstrated_levels": demonstrated_levels,
            "question_results": [qr.model_dump() for qr in question_results]
        }

        updated = await assessments_repo.update({"assessment_id": payload.assessment_id}, update_payload)

        result_response = AssessmentResultResponse(
            assessment_id=payload.assessment_id,
            user_id=assessment.get("user_id", user_id),
            target_role=target_role,
            total_questions=total_answered,
            correct_answers=correct_count,
            score_percentage=score_pct,
            category_scores=category_scores,
            demonstrated_skill_scores=demonstrated_skill_scores,
            demonstrated_levels=demonstrated_levels,
            question_results=question_results,
            completed_at=updated.get("updated_at", "")
        )

        return AdaptiveNextResponse(
            assessment_id=payload.assessment_id,
            question_number=total_answered,
            total_questions=total_answered,
            feedback=feedback,
            next_question=None,
            is_completed=True,
            result=result_response,
            policy_version="ADAPT-v1.0-baseline"
        )

    # Next question available - persist state and advance
    update_payload = {
        "answered_questions": answered_questions,
        "current_question_server": next_q
    }
    await assessments_repo.update({"assessment_id": payload.assessment_id}, update_payload)

    client_next_q = AssessmentQuestion(
        id=next_q["id"],
        question=next_q["question"],
        options=next_q["options"],
        skill=next_q["skill"],
        difficulty=next_q["difficulty"]
    )

    return AdaptiveNextResponse(
        assessment_id=payload.assessment_id,
        question_number=len(answered_questions) + 1,
        total_questions=max_q,
        feedback=feedback,
        next_question=client_next_q,
        is_completed=False,
        result=None,
        policy_version="ADAPT-v1.0-baseline"
    )

@router.get("/adaptive/{assessment_id}", response_model=AdaptiveStartResponse)
async def get_adaptive_session(
    assessment_id: str,
    user_id: str = Depends(get_optional_user_id)
):
    """Fetches the active in-progress adaptive assessment question for session continuity."""
    assessment = await assessments_repo.find_one({"assessment_id": assessment_id})
    verify_resource_ownership(assessment, user_id, "Adaptive assessment")

    if assessment.get("status") == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment has already been completed."
        )

    current_q = assessment.get("current_question_server")
    if not current_q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active question found for this assessment session."
        )

    answered = assessment.get("answered_questions", [])
    max_q = assessment.get("max_questions", 5)

    client_q = AssessmentQuestion(
        id=current_q["id"],
        question=current_q["question"],
        options=current_q["options"],
        skill=current_q["skill"],
        difficulty=current_q["difficulty"]
    )

    return AdaptiveStartResponse(
        assessment_id=assessment_id,
        target_role=assessment.get("target_role", "Full Stack Developer"),
        question_number=len(answered) + 1,
        total_questions=max_q,
        question=client_q,
        is_completed=False,
        policy_version="ADAPT-v1.0-baseline",
        created_at=assessment.get("created_at", "")
    )

# ---------------------------------------------------------------------------
# BATCH ASSESSMENT (Preserved for compatibility and bulk evaluation)
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=AssessmentSessionResponse)
async def generate_assessment(
    payload: AssessmentGenerateRequest,
    user_id: str = Depends(get_optional_user_id)
):
    session_data = generate_assessment_for_role(
        target_role=payload.target_role,
        user_skills=payload.skills,
        num_questions=payload.num_questions,
        difficulty_preference=payload.difficulty_preference or "balanced"
    )

    assessment_id = session_data["assessment_id"]
    record = {
        "assessment_id": assessment_id,
        "user_id": user_id,
        "target_role": payload.target_role,
        "questions_count": session_data["total_questions"],
        "_server_questions": session_data["_server_questions"],
        "client_questions": session_data["questions"],
        "status": "in_progress"
    }

    saved = await assessments_repo.insert(record)

    questions_models = [AssessmentQuestion(**q) for q in session_data["questions"]]

    return AssessmentSessionResponse(
        assessment_id=assessment_id,
        target_role=payload.target_role,
        questions=questions_models,
        total_questions=len(questions_models),
        created_at=saved["created_at"]
    )

@router.post("/submit", response_model=AssessmentResultResponse)
async def submit_assessment(
    payload: AssessmentSubmitRequest,
    user_id: str = Depends(get_optional_user_id)
):
    assessment = await assessments_repo.find_one({"assessment_id": payload.assessment_id})
    verify_resource_ownership(assessment, user_id, "Assessment session")

    server_questions = assessment.get("_server_questions", [])
    if not server_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment question data is missing or corrupted."
        )

    grading = grade_assessment(server_questions, payload.answers)

    update_payload = {
        "status": "completed",
        "user_answers": payload.answers,
        "score_percentage": grading["score_percentage"],
        "correct_answers": grading["correct_answers"],
        "category_scores": grading["category_scores"],
        "demonstrated_skill_scores": grading["demonstrated_skill_scores"],
        "demonstrated_levels": grading["demonstrated_levels"],
        "question_results": grading["question_results"]
    }

    updated = await assessments_repo.update({"assessment_id": payload.assessment_id}, update_payload)

    return AssessmentResultResponse(
        assessment_id=payload.assessment_id,
        user_id=assessment.get("user_id", user_id),
        target_role=assessment.get("target_role", "Full Stack Developer"),
        total_questions=grading["total_questions"],
        correct_answers=grading["correct_answers"],
        score_percentage=grading["score_percentage"],
        category_scores=grading["category_scores"],
        demonstrated_skill_scores=grading["demonstrated_skill_scores"],
        demonstrated_levels=grading["demonstrated_levels"],
        question_results=[QuestionResult(**qr) for qr in grading["question_results"]],
        completed_at=updated.get("updated_at", "")
    )

@router.get("/{assessment_id}", response_model=Optional[AssessmentResultResponse])
async def get_assessment_result(
    assessment_id: str,
    user_id: str = Depends(get_optional_user_id)
):
    assessment = await assessments_repo.find_one({"assessment_id": assessment_id})
    verify_resource_ownership(assessment, user_id, "Assessment result")

    if assessment.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Assessment has not been completed yet.")

    return AssessmentResultResponse(
        assessment_id=assessment_id,
        user_id=assessment.get("user_id", user_id),
        target_role=assessment.get("target_role", "Full Stack Developer"),
        total_questions=len(assessment.get("question_results", [])),
        correct_answers=assessment.get("correct_answers", 0),
        score_percentage=assessment.get("score_percentage", 0.0),
        category_scores=assessment.get("category_scores", {}),
        demonstrated_skill_scores=assessment.get("demonstrated_skill_scores", {}),
        demonstrated_levels=assessment.get("demonstrated_levels", {}),
        question_results=[QuestionResult(**qr) for qr in assessment.get("question_results", [])],
        completed_at=assessment.get("updated_at", "")
    )
