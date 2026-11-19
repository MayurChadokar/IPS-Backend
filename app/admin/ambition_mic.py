from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.admin.routes import require_admin, templates
from app.core.database import get_db
from app.models.models import AmbitionMicSubmission, User


router = APIRouter()


@router.get("/ambition-mic", response_class=HTMLResponse)
def list_entries(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    query = db.query(AmbitionMicSubmission)
    total = query.count()
    entries = query.order_by(AmbitionMicSubmission.id.desc()).offset((page - 1) * 20).limit(20).all()
    return templates.TemplateResponse("admin/ambition_mic/list.html", {
        "request": request, "user": user, "entries": entries, "total": total,
        "page_number": page, "has_next": page * 20 < total,
    })


@router.get("/ambition-mic/{entry_id}", response_class=HTMLResponse)
def entry_detail(
    request: Request,
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    entry = db.get(AmbitionMicSubmission, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return templates.TemplateResponse("admin/ambition_mic/detail.html", {
        "request": request, "user": user, "entry": entry,
    })
