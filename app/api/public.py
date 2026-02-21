from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import College, Page, Section, SectionContent, Faculty, Course, Inquiry, News, Event
from app.schemas.schemas import (
    PagePublicResponse,
    InquiryCreate,
    NewsListItem,
    NewsDetail,
    EventListItem,
    EventDetail,
)
from typing import Dict, Any
from typing import List, Dict, Any


router = APIRouter()


@router.get("/{college_slug}/pages/{page_slug:path}", response_model=PagePublicResponse)
async def get_page_by_college(
    college_slug: str,
    page_slug: str,
    db: Session = Depends(get_db)
):
    """
    Public API endpoint for frontend
    
    Example:
    - GET /api/ipsa/pages/home
    - GET /api/college-a/pages/about-us
    
    Returns page data with all sections organized by section_key
    """
    
    # Find college
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()
    
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College '{college_slug}' not found"
        )
    
    # Find page
    page = db.query(Page).filter(
        Page.college_id == college.id,
        Page.slug == page_slug,
        Page.is_active == True
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{page_slug}' not found for college '{college_slug}'"
        )
    
    # Get all active sections with content
    sections = db.query(Section).filter(
        Section.page_id == page.id,
        Section.is_active == True
    ).order_by(Section.sort_order).all()
    
    # Build sections dictionary
    sections_dict: Dict[str, Any] = {}
    for section in sections:
        content_data = {}
        if section.content:
            content_data = section.content.content_json
        
        sections_dict[section.section_key] = {
            "type": section.section_type,
            "sort_order": section.sort_order,
            **content_data
        }
    
    return PagePublicResponse(
        college=college_slug,
        page=page_slug,
        title=page.title,
        meta_description=page.meta_description,
        sections=sections_dict
    )


@router.get("/{college_slug}/pages", response_model=List[Dict[str, Any]])
async def list_pages_by_college(
    college_slug: str,
    db: Session = Depends(get_db)
):
    """
    List all active pages for a college
    
    Example: GET /api/ipsa/pages
    Returns: [{"slug": "home", "title": "Home"}, ...]
    """
    
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()
    
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College '{college_slug}' not found"
        )
    
    pages = db.query(Page).filter(
        Page.college_id == college.id,
        Page.is_active == True
    ).all()
    
    return [
        {
            "slug": page.slug,
            "title": page.title,
            "meta_description": page.meta_description
        }
        for page in pages
    ]



@router.get("/{college_slug}/news", response_model=List[NewsListItem])
async def list_news_by_college(
    college_slug: str,
    db: Session = Depends(get_db)
):
    """
    List published news for a college
    Example: GET /api/ipsa/news
    """
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()

    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    items = db.query(News).filter(
        News.college_id == college.id,
        News.is_published == True
    ).order_by(News.published_at.desc().nullslast()).all()

    return [
        NewsListItem(
            id=n.id,
            title=n.title,
            subtitle=n.subtitle,
            thumbnail_image=n.thumbnail_image,
            short_description=n.short_description,
            published_at=n.published_at,
        )
        for n in items
    ]


@router.get("/{college_slug}/news/{news_id}", response_model=NewsDetail)
async def get_news_detail(
    college_slug: str,
    news_id: int,
    db: Session = Depends(get_db)
):
    college = db.query(College).filter(College.slug == college_slug, College.is_active == True).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    n = db.query(News).filter(News.id == news_id, News.college_id == college.id).first()
    if not n or not n.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    return NewsDetail(
        id=n.id,
        title=n.title,
        subtitle=n.subtitle,
        content_html=n.content_html,
        thumbnail_image=n.thumbnail_image,
        short_description=n.short_description,
        published_at=n.published_at,
    )


@router.get("/{college_slug}/events", response_model=List[EventListItem])
async def list_events_by_college(
    college_slug: str,
    db: Session = Depends(get_db)
):
    """
    List active events for a college
    """
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()

    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    items = db.query(Event).filter(
        Event.college_id == college.id,
        Event.is_active == True
    ).order_by(Event.start_date.desc().nullslast()).all()

    return [
        EventListItem(
            id=e.id,
            title=e.title,
            subtitle=e.subtitle,
            thumbnail_image=e.thumbnail_image,
            short_description=e.short_description,
            start_date=e.start_date,
            end_date=e.end_date,
        )
        for e in items
    ]


@router.get("/{college_slug}/events/{event_id}", response_model=EventDetail)
async def get_event_detail(
    college_slug: str,
    event_id: int,
    db: Session = Depends(get_db)
):
    college = db.query(College).filter(College.slug == college_slug, College.is_active == True).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    e = db.query(Event).filter(Event.id == event_id, Event.college_id == college.id).first()
    if not e or not e.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return EventDetail(
        id=e.id,
        title=e.title,
        subtitle=e.subtitle,
        content_html=e.content_html,
        thumbnail_image=e.thumbnail_image,
        short_description=e.short_description,
        location=e.location,
        start_date=e.start_date,
        end_date=e.end_date,
    )


@router.get("/colleges", response_model=List[Dict[str, Any]])
async def list_active_colleges(db: Session = Depends(get_db)):
    """
    List all active colleges
    
    Example: GET /api/colleges
    """
    colleges = db.query(College).filter(College.is_active == True).all()
    
    return [
        {
            "slug": college.slug,
            "name": college.name,
            "logo": college.logo,
            "domain": college.domain
        }
        for college in colleges
    ]


@router.get("/{college_slug}/faculties", response_model=List[Dict[str, Any]])
async def list_faculties_by_college(
    college_slug: str,
    db: Session = Depends(get_db)
):
    """
    List all active faculties for a college
    
    Example: GET /api/ipsa/faculties
    """
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()
    
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College '{college_slug}' not found"
        )
    
    faculties = db.query(Faculty).filter(
        Faculty.college_id == college.id,
        Faculty.is_active == True
    ).all()
    
    return [
        {
            "id": faculty.id,
            "name": faculty.name,
            "email": faculty.email,
            "contact": faculty.contact,
            "image": faculty.image,
            "designation": faculty.designation,
            "department": faculty.department,
            "description":faculty.description
        }
        for faculty in faculties
    ]


@router.get("/{college_slug}/courses", response_model=List[Dict[str, Any]])
async def list_courses_by_college(
    college_slug: str,
    db: Session = Depends(get_db)
):
    """
    List all active courses for a college
    
    Example: GET /api/ipsa/courses
    """
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()
    
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College '{college_slug}' not found"
        )
    
    courses = db.query(Course).filter(
        Course.college_id == college.id,
        Course.is_active == True
    ).all()
    
    return [
        {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "eligibility": course.eligibility,
            "fee_structure": course.fee_structure
        }
        for course in courses
    ]


@router.post("/{college_slug}/inquiry", status_code=status.HTTP_201_CREATED)
async def submit_inquiry(
    college_slug: str,
    inquiry: InquiryCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a new inquiry form
    """
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()
    
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College '{college_slug}' not found"
        )
    
    new_inquiry = Inquiry(
        college_id=college.id,
        name=inquiry.name,
        email=inquiry.email,
        phone_number=inquiry.phone_number,
        course_interested=inquiry.course_interested,
        message=inquiry.message
    )
    
    db.add(new_inquiry)
    db.commit()
    db.refresh(new_inquiry)
    
    return {"message": "Inquiry submitted successfully", "id": new_inquiry.id}
