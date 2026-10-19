from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_admin
from app.models.models import CareerOpening
from app.schemas.careers import (
    CareerFilterOptions, CareerOpeningCreate, CareerOpeningList,
    CareerOpeningResponse, CareerOpeningUpdate, CareerPageSettings,
)
from app.services.careers import filter_options, get_college, get_opening, get_page_settings, opening_query, save_page_settings


public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(get_current_active_admin)])


@public_router.get("/{college_slug}/careers/filters", response_model=CareerFilterOptions)
def public_career_filters(college_slug: str, db: Session = Depends(get_db)):
    college = get_college(db, slug=college_slug, public=True)
    return filter_options(db, college.id)


@public_router.get("/{college_slug}/careers", response_model=CareerOpeningList)
def public_careers(
    college_slug: str,
    keywords: str = Query("", max_length=255),
    category: str = Query("", max_length=100),
    job_type: str = Query("", max_length=100),
    location: str = Query("", max_length=255),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    college = get_college(db, slug=college_slug, public=True)
    query = opening_query(db, college.id, public=True, keywords=keywords, category=category, job_type=job_type, location=location)
    return {
        "items": query.order_by(CareerOpening.sort_order, CareerOpening.posted_date.desc(), CareerOpening.created_at.desc(), CareerOpening.id.desc()).offset((page - 1) * page_size).limit(page_size).all(),
        "total": query.count(), "page": page, "page_size": page_size,
    }


@public_router.get("/{college_slug}/careers/{opening_id}", response_model=CareerOpeningResponse)
def public_career_detail(college_slug: str, opening_id: int, db: Session = Depends(get_db)):
    college = get_college(db, slug=college_slug, public=True)
    return get_opening(db, college.id, opening_id, public=True)


@admin_router.get("/colleges/{college_id}/career-page", response_model=CareerPageSettings)
def admin_career_page(college_id: int, db: Session = Depends(get_db)):
    get_college(db, college_id=college_id)
    return get_page_settings(db, college_id)


@admin_router.put("/colleges/{college_id}/career-page", response_model=CareerPageSettings)
def update_career_page(college_id: int, settings: CareerPageSettings, db: Session = Depends(get_db)):
    college = get_college(db, college_id=college_id)
    save_page_settings(db, college, settings)
    db.commit()
    return get_page_settings(db, college_id)


@admin_router.get("/colleges/{college_id}/careers", response_model=CareerOpeningList)
def admin_careers(college_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    get_college(db, college_id=college_id)
    query = opening_query(db, college_id)
    return {"items": query.order_by(CareerOpening.sort_order, CareerOpening.id.desc()).offset((page - 1) * page_size).limit(page_size).all(), "total": query.count(), "page": page, "page_size": page_size}


@admin_router.post("/colleges/{college_id}/careers", response_model=CareerOpeningResponse, status_code=status.HTTP_201_CREATED)
def create_career(college_id: int, data: CareerOpeningCreate, db: Session = Depends(get_db)):
    get_college(db, college_id=college_id)
    opening = CareerOpening(college_id=college_id, **data.model_dump())
    db.add(opening)
    db.commit()
    db.refresh(opening)
    return opening


@admin_router.get("/colleges/{college_id}/careers/{opening_id}", response_model=CareerOpeningResponse)
def admin_career_detail(college_id: int, opening_id: int, db: Session = Depends(get_db)):
    get_college(db, college_id=college_id)
    return get_opening(db, college_id, opening_id)


@admin_router.put("/colleges/{college_id}/careers/{opening_id}", response_model=CareerOpeningResponse)
def update_career(college_id: int, opening_id: int, data: CareerOpeningUpdate, db: Session = Depends(get_db)):
    get_college(db, college_id=college_id)
    opening = get_opening(db, college_id, opening_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(opening, field, value)
    db.commit()
    db.refresh(opening)
    return opening


@admin_router.delete("/colleges/{college_id}/careers/{opening_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_career(college_id: int, opening_id: int, db: Session = Depends(get_db)):
    get_college(db, college_id=college_id)
    opening = get_opening(db, college_id, opening_id)
    db.delete(opening)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
