from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import College, Page, Section, SectionContent
from app.schemas.schemas import PagePublicResponse
from typing import Dict, Any


router = APIRouter()


@router.get("/{college_slug}/pages/{page_slug}", response_model=PagePublicResponse)
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


@router.get("/{college_slug}/pages", response_model=list[Dict[str, Any]])
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


@router.get("/colleges", response_model=list[Dict[str, Any]])
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
