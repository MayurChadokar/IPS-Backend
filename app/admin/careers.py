import io
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.admin.routes import require_admin, templates
from app.core.cloudinary import get_public_id_from_url, upload_image
from app.core.config import settings
from app.core.database import get_db
from app.models.models import CareerOpening, User, UserRole
from app.schemas.careers import CareerOpeningCreate, CareerPageSettings
from app.services.careers import career_today, filter_options, get_career_page, get_college, get_opening, get_page_settings, opening_query, save_page_settings


router = APIRouter()


def require_career_admin(user: User = Depends(require_admin)):
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return user


def validation_message(error):
    return "; ".join(f"{item['loc'][-1]}: {item['msg']}" for item in error.errors())


@router.get("/careers")
def ipsa_careers(db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    college = get_college(db, slug="ipsa")
    return RedirectResponse(f"/admin/colleges/{college.id}/careers", status_code=303)


@router.get("/colleges/{college_id}/careers", response_class=HTMLResponse)
def list_careers(request: Request, college_id: int, page: int = Query(1, ge=1), db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    college = get_college(db, college_id=college_id)
    query = opening_query(db, college_id)
    total = query.count()
    return templates.TemplateResponse("admin/careers/list.html", {
        "request": request, "user": user, "college": college,
        "openings": query.order_by(CareerOpening.sort_order, CareerOpening.id.desc()).offset((page - 1) * 20).limit(20).all(),
        "total": total, "page_number": page, "has_next": page * 20 < total,
        "career_page": get_career_page(db, college_id), "today": career_today(),
    })


def opening_form(request, db, user, college, values, action, error=None):
    options = filter_options(db, college.id)
    return templates.TemplateResponse("admin/careers/form.html", {
        "request": request, "user": user, "college": college,
        "values": values, "action": action, "options": options, "error": error,
    }, status_code=422 if error else 200)


@router.get("/colleges/{college_id}/careers/new", response_class=HTMLResponse)
def new_career(request: Request, college_id: int, db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    college = get_college(db, college_id=college_id)
    settings = get_page_settings(db, college_id)
    return opening_form(request, db, user, college, {"category": settings["categories"][0], "job_type": settings["job_types"][0], "location": "Indore", "posted_date": career_today().isoformat(), "sort_order": 0, "is_active": True}, "Create")


async def opening_form_data(request, default_posted_date=None):
    form = await request.form()
    return {
        **{field: form.get(field, "") for field in ("title", "category", "job_type", "location", "description", "apply_url")},
        **{field: form.get(field) or None for field in ("department", "short_description", "qualifications", "closing_date")},
        "posted_date": form.get("posted_date", (default_posted_date or career_today()).isoformat()),
        "sort_order": form.get("sort_order", "0"), "is_active": form.get("is_active") == "true",
    }


@router.post("/colleges/{college_id}/careers/new")
async def create_career(request: Request, college_id: int, db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    college = get_college(db, college_id=college_id)
    values = await opening_form_data(request)
    try:
        data = CareerOpeningCreate.model_validate(values)
    except ValidationError as error:
        return opening_form(request, db, user, college, values, "Create", validation_message(error))
    db.add(CareerOpening(college_id=college_id, **data.model_dump()))
    db.commit()
    return RedirectResponse(f"/admin/colleges/{college_id}/careers", status_code=303)


@router.get("/colleges/{college_id}/careers/{opening_id}/edit", response_class=HTMLResponse)
def edit_career(request: Request, college_id: int, opening_id: int, db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    college = get_college(db, college_id=college_id)
    opening = get_opening(db, college_id, opening_id)
    values = CareerOpeningCreate.model_validate(opening).model_dump()
    for field in ("posted_date", "closing_date"):
        if values[field]:
            values[field] = values[field].isoformat()
    return opening_form(request, db, user, college, values, "Edit")


@router.post("/colleges/{college_id}/careers/{opening_id}/edit")
async def update_career(request: Request, college_id: int, opening_id: int, db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    college = get_college(db, college_id=college_id)
    opening = get_opening(db, college_id, opening_id)
    values = await opening_form_data(request, default_posted_date=opening.posted_date)
    try:
        data = CareerOpeningCreate.model_validate(values)
    except ValidationError as error:
        return opening_form(request, db, user, college, values, "Edit", validation_message(error))
    for field, value in data.model_dump().items():
        setattr(opening, field, value)
    db.commit()
    return RedirectResponse(f"/admin/colleges/{college_id}/careers", status_code=303)


@router.post("/colleges/{college_id}/careers/{opening_id}/delete")
def delete_career(college_id: int, opening_id: int, db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    opening = get_opening(db, college_id, opening_id)
    db.delete(opening)
    db.commit()
    return RedirectResponse(f"/admin/colleges/{college_id}/careers", status_code=303)


def page_form(request, user, college, values, error=None, saved=False):
    return templates.TemplateResponse("admin/careers/page.html", {
        "request": request, "user": user, "college": college,
        "values": values, "error": error, "saved": saved,
        "max_upload_size_mb": f"{settings.MAX_UPLOAD_SIZE / (1024 * 1024):g}",
    }, status_code=422 if error else 200)


@router.get("/colleges/{college_id}/careers/page", response_class=HTMLResponse)
def career_page_form(request: Request, college_id: int, saved: bool = False, db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    college = get_college(db, college_id=college_id)
    return page_form(request, user, college, get_page_settings(db, college_id), saved=saved)


@router.post("/colleges/{college_id}/careers/page")
async def update_career_page(request: Request, college_id: int, banner_image: Optional[UploadFile] = File(None), db: Session = Depends(get_db), user: User = Depends(require_career_admin)):
    college = get_college(db, college_id=college_id)
    form = await request.form()
    values = {field: form.get(field, "") for field in ("title", "meta_description", "hero_image", "hero_alt", "introduction_title", "introduction_description", "openings_title")}
    values.update(categories=[line.strip() for line in form.get("categories", "").splitlines() if line.strip()], job_types=[line.strip() for line in form.get("job_types", "").splitlines() if line.strip()], is_active=form.get("is_active") == "true")
    try:
        validation_values = {**values, "hero_image": ""} if banner_image and banner_image.filename else values
        data = CareerPageSettings.model_validate(validation_values)
    except ValidationError as error:
        return page_form(request, user, college, values, validation_message(error))
    if banner_image and banner_image.filename:
        image_bytes = await banner_image.read(settings.MAX_UPLOAD_SIZE + 1)
        if len(image_bytes) > settings.MAX_UPLOAD_SIZE:
            return page_form(request, user, college, values, f"Banner image exceeds the {settings.MAX_UPLOAD_SIZE / (1024 * 1024):g} MB size limit.")
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                image_format = image.format
                image.verify()
            if image_format not in ("JPEG", "PNG", "WEBP"):
                return page_form(request, user, college, values, "Upload a JPG, PNG or WebP banner image.")
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            return page_form(request, user, college, values, "Upload a valid JPG, PNG or WebP banner image.")
        extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image_format]
        try:
            uploaded_url = await run_in_threadpool(
                upload_image, io.BytesIO(image_bytes), folder=f"careers/{college.id}",
                filename=f"career-banner-{uuid4().hex}.{extension}", convert_to_webp=False,
            )
        except OSError:
            return page_form(request, user, college, values, "The banner image could not be saved. Please try again.")
        # A site-relative URL works with the uploads mounted by this backend,
        # including when the dashboard is running locally.
        data.hero_image = f"/uploads/{get_public_id_from_url(uploaded_url)}"
    save_page_settings(db, college, data)
    db.commit()
    return RedirectResponse(f"/admin/colleges/{college_id}/careers/page?saved=true", status_code=303)
