"""Shared career queries and the existing CMS page/section integration."""
from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.dates import india_today as career_today
from app.models.models import CareerOpening, College, Page, Section, SectionContent
from app.schemas.careers import CareerPageSettings


def get_college(db: Session, *, college_id=None, slug=None, public=False):
    query = db.query(College)
    query = query.filter(College.id == college_id) if college_id is not None else query.filter(College.slug == slug)
    if public:
        query = query.filter(College.is_active.is_(True))
    college = query.first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return college


def opening_query(db: Session, college_id: int, *, public=False, keywords=None, category=None, job_type=None, location=None):
    query = db.query(CareerOpening).filter(CareerOpening.college_id == college_id)
    if public:
        query = query.filter(
            CareerOpening.is_active.is_(True),
            or_(CareerOpening.closing_date.is_(None), CareerOpening.closing_date >= career_today()),
        )
    if keywords and keywords.strip():
        keyword = keywords.strip().lower()
        query = query.filter(or_(*[
            func.lower(column).contains(keyword, autoescape=True)
            for column in (CareerOpening.title, CareerOpening.description, CareerOpening.department, CareerOpening.short_description)
        ]))
    for column, value in ((CareerOpening.category, category), (CareerOpening.job_type, job_type), (CareerOpening.location, location)):
        if value and value.strip():
            query = query.filter(func.lower(column) == value.strip().lower())
    return query


def get_opening(db: Session, college_id: int, opening_id: int, *, public=False):
    opening = opening_query(db, college_id, public=public).filter(CareerOpening.id == opening_id).first()
    if not opening:
        raise HTTPException(status_code=404, detail="Career opening not found")
    return opening


def get_career_page(db: Session, college_id: int):
    return db.query(Page).filter(Page.college_id == college_id, Page.slug == "career").first()


def get_page_settings(db: Session, college_id: int):
    settings = CareerPageSettings().model_dump()
    page = get_career_page(db, college_id)
    if not page:
        return settings
    settings.update(title=page.title, meta_description=page.meta_description or "", is_active=page.is_active)
    for section in page.sections:
        content = section.content.content_json if section.content else {}
        if section.section_key == "hero":
            images = content.get("images") or []
            settings.update(hero_image=images[0] if images else "", hero_alt=content.get("alt", settings["hero_alt"]))
        elif section.section_key == "career_introduction":
            settings.update(introduction_title=content.get("title", settings["introduction_title"]), introduction_description=content.get("description", settings["introduction_description"]))
        elif section.section_key == "current_openings":
            settings.update(openings_title=content.get("title", settings["openings_title"]), categories=content.get("categories", settings["categories"]), job_types=content.get("job_types", settings["job_types"]))
    return settings


def save_page_settings(db: Session, college: College, settings: CareerPageSettings):
    page = get_career_page(db, college.id)
    if not page:
        page = Page(college_id=college.id, slug="career", title=settings.title)
        db.add(page)
        db.flush()
    page.title = settings.title
    page.meta_title = settings.title
    page.meta_description = settings.meta_description
    page.is_active = settings.is_active
    sections = [
        ("hero", "hero", {"images": [settings.hero_image] if settings.hero_image else [], "alt": settings.hero_alt}),
        ("career_introduction", "text", {"title": settings.introduction_title, "description": settings.introduction_description}),
        ("current_openings", "custom", {"title": settings.openings_title, "categories": settings.categories, "job_types": settings.job_types, "api_endpoint": f"/api/{college.slug}/careers", "filters_endpoint": f"/api/{college.slug}/careers/filters", "apply_button_text": "Apply Now"}),
    ]
    for order, (key, kind, content) in enumerate(sections, 1):
        section = db.query(Section).filter(Section.page_id == page.id, Section.section_key == key).first()
        if not section:
            section = Section(college_id=college.id, page_id=page.id, section_key=key, section_type=kind, sort_order=order, is_active=True)
            db.add(section)
            db.flush()
        if section.content:
            section.content.content_json = {**section.content.content_json, **content}
        else:
            db.add(SectionContent(section_id=section.id, content_json=content))
    return page


def filter_options(db: Session, college_id: int):
    settings = get_page_settings(db, college_id)
    rows = opening_query(db, college_id, public=True).with_entities(CareerOpening.category, CareerOpening.job_type, CareerOpening.location).distinct().all()

    def options(defaults, values):
        result = []
        seen = set()
        for value in [*defaults, *sorted(set(values))]:
            if value and value.casefold() not in seen:
                result.append(value)
                seen.add(value.casefold())
        return result

    return {
        "categories": options(settings["categories"], [row.category for row in rows]),
        "job_types": options(settings["job_types"], [row.job_type for row in rows]),
        "locations": options([], [row.location for row in rows]),
    }
