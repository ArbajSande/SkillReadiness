from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from typing import Optional, Dict, Any, List
from app.models.schemas import ResumeUploadResponse, SkillItem, SkillExtractRequest
from app.core.security import get_optional_user_id, verify_resource_ownership
from app.core.repository import resumes_repo
from app.core.config import settings
from app.services.skill_engine import extract_text_from_file, extract_skills_from_text

router = APIRouter(prefix="/api/resume", tags=["Resume & Skills"])

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    target_role: Optional[str] = Form("Full Stack Developer"),
    user_id: str = Depends(get_optional_user_id)
):
    raw_text = ""
    filename = "pasted_text.txt"

    if file:
        filename = file.filename or "uploaded_resume.pdf"
        file_bytes = await file.read()
        if not file_bytes or len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")
        if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded file exceeds maximum allowed size of {max_mb} MB."
            )
        try:
            raw_text = extract_text_from_file(filename, file_bytes)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process file format: {str(e)}")
    elif text_content is not None:
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Provided resume text is empty or contains only whitespace.")
        raw_text = text_content.strip()
    else:
        raise HTTPException(
            status_code=400,
            detail="Please provide either a valid resume file (PDF, DOCX, TXT) or raw resume text."
        )

    if len(raw_text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from the provided document. Please check file format."
        )

    # Extract skills using NLP engine with negation safety
    extracted_skills_raw = extract_skills_from_text(raw_text, target_role=target_role or "Full Stack Developer")

    skill_items = [
        SkillItem(
            name=s["name"],
            category=s["category"],
            proficiency_level=s["proficiency_level"],
            confidence_score=s["confidence_score"],
            source=s.get("source", "resume_extracted"),
            evidence_count=s.get("evidence_count", 1)
        )
        for s in extracted_skills_raw
    ]

    resume_record = {
        "user_id": user_id,
        "filename": filename,
        "extracted_skills": [s.model_dump() for s in skill_items],
        "total_skills": len(skill_items),
        "raw_text_preview": raw_text[:500] + ("..." if len(raw_text) > 500 else ""),
        "target_role": target_role
    }

    saved_doc = await resumes_repo.insert(resume_record)

    return ResumeUploadResponse(
        id=saved_doc["id"],
        user_id=user_id,
        filename=filename,
        extracted_skills=skill_items,
        total_skills=len(skill_items),
        raw_text_preview=saved_doc["raw_text_preview"],
        target_role=target_role,
        created_at=saved_doc["created_at"]
    )

@router.post("/extract-skills", response_model=List[SkillItem])
async def extract_skills_raw(payload: SkillExtractRequest):
    if not payload.text or len(payload.text.strip()) < 5:
        return []
    extracted_raw = extract_skills_from_text(payload.text, target_role=payload.target_role or "Full Stack Developer")
    return [
        SkillItem(
            name=s["name"],
            category=s["category"],
            proficiency_level=s["proficiency_level"],
            confidence_score=s["confidence_score"],
            source=s.get("source", "raw_text"),
            evidence_count=s.get("evidence_count", 1)
        )
        for s in extracted_raw
    ]

@router.get("/latest", response_model=Optional[ResumeUploadResponse])
async def get_latest_resume(user_id: str = Depends(get_optional_user_id)):
    recent = await resumes_repo.find_many({"user_id": user_id}, limit=1)
    if not recent:
        return None
    doc = recent[0]
    return ResumeUploadResponse(
        id=doc["id"],
        user_id=doc["user_id"],
        filename=doc.get("filename", "resume"),
        extracted_skills=[SkillItem(**s) for s in doc.get("extracted_skills", [])],
        total_skills=doc.get("total_skills", 0),
        raw_text_preview=doc.get("raw_text_preview", ""),
        target_role=doc.get("target_role"),
        created_at=doc.get("created_at", "")
    )
