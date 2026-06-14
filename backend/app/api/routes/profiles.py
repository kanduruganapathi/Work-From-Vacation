"""Candidate profile routes."""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Profile, User
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileOut | None)
def get_profile(current_user: User = Depends(get_current_user)) -> Profile | None:
    return current_user.profile


@router.put("", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = current_user.profile
    if profile is None:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/resume", response_model=ProfileOut)
async def upload_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    """Upload a resume (PDF or plain text) and store its extracted text.

    The extracted text feeds the matching, resume-tailoring, and cover-letter
    agents.
    """
    raw = await file.read()
    if len(raw) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="Resume exceeds 5 MB limit.")

    name = (file.filename or "").lower()
    content_type = file.content_type or ""
    if name.endswith(".pdf") or "pdf" in content_type:
        text = _extract_pdf_text(raw)
    else:
        text = raw.decode("utf-8", errors="ignore")

    text = text.strip()
    if not text:
        raise HTTPException(
            status_code=400, detail="Could not extract any text from the file."
        )

    profile = current_user.profile
    if profile is None:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
    profile.resume_text = text
    db.commit()
    db.refresh(profile)
    return profile


def _extract_pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # corrupt / unsupported PDF
        raise HTTPException(
            status_code=400, detail=f"Could not read PDF: {exc}"
        ) from exc
