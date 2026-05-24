
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import asyncio
from app.core.database import get_db
from app.services.meritto_crm import meritto_service
from app.models.models import College, Page, Section, SectionContent, Faculty, Course, Inquiry, Contact, News, Event, Activity, Alumni, SocialMediaLink
from app.schemas.schemas import (
    PagePublicResponse,
    InquiryCreate,
    ContactCreate,
    NewsListItem,
    NewsDetail,
    EventListItem,
    EventDetail,
    ActivityListItem,
    ActivityDetail,
    AlumniListItem,
    AlumniDetail,
    CollegePublicInfo,
)
from typing import List, Dict, Any, Optional


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
        meta_title=page.meta_title,
        meta_keywords=page.meta_keywords,
        canonical_url=page.canonical_url,
        robots=page.robots,
        og_title=page.og_title,
        og_description=page.og_description,
        og_image=page.og_image,
        twitter_title=page.twitter_title,
        twitter_description=page.twitter_description,
        twitter_image=page.twitter_image,
        schema_markup=page.schema_markup,
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
    ).order_by((News.published_at == None).asc(), News.published_at.desc()).all()

    return [
        NewsListItem(
            id=n.id,
            title=n.title,
            subtitle=n.subtitle,
            thumbnail_image=n.thumbnail_image,
            short_description=n.short_description,
            gallery_images=n.gallery_images,
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
        gallery_images=n.gallery_images,
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
    ).order_by((Event.start_date == None).asc(), Event.start_date.desc()).all()

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


@router.get("/{college_slug}/info", response_model=CollegePublicInfo)
async def get_college_info(
    college_slug: str,
    db: Session = Depends(get_db)
):
    """
    Get college information including its name, logo, pages, and social media links.
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
    
    # Get all active pages
    pages = db.query(Page).filter(
        Page.college_id == college.id,
        Page.is_active == True
    ).all()
    
    pages_list = [
        {
            "slug": page.slug,
            "title": page.title,
            "meta_description": page.meta_description
        }
        for page in pages
    ]
    
    # Get all active social media links
    social_links = db.query(SocialMediaLink).filter(
        SocialMediaLink.college_id == college.id,
        SocialMediaLink.is_active == True
    ).all()
    
    social_list = [
        {
            "platform": link.platform.value,
            "url": link.url
        }
        for link in social_links
    ]
    
    return CollegePublicInfo(
        name=college.name,
        slug=college.slug,
        logo=college.logo,
        footer_logo=college.footer_logo,
        document_download_link=college.document_download_link,
        domain=college.domain,
        pages=pages_list,
        social_media_links=social_list
    )


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


@router.get("/{college_slug}/courses/names", response_model=List[str])
async def list_course_names_by_college(
    college_slug: str,
    db: Session = Depends(get_db)
):
    """
    Return only the course names for a given college slug.

    Example: GET /api/ipsa/courses/names
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

    return [c.name for c in courses]


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
    
    print(f"[ENDPOINT] New inquiry created - ID: {new_inquiry.id}, Email: {inquiry.email}")
    print(
        f"[ENDPOINT][INQUIRY] Local payload: name={inquiry.name}, email={inquiry.email}, "
        f"phone_number={inquiry.phone_number}, state={inquiry.state}, city={inquiry.city}, "
        f"course_interested={inquiry.course_interested}, c_course={inquiry.c_course}, "
        f"----------specialization={inquiry.c_specialization}-------------"
    )
    
    # Send to Meritto CRM in parallel (non-blocking)
    # specialization = inquiry.c_specialization
    meritto_payload = {
        "inquiry_id": new_inquiry.id,
        "name": inquiry.name,
        "email": inquiry.email,
        "phone_number": inquiry.phone_number,
        "state": inquiry.state,
        "city": inquiry.city,
        "course_interested": inquiry.course_interested,
        "message": inquiry.message,
        "college_name": college.name,
        "c_course": inquiry.c_course,
        "specialization": inquiry.c_specialization,
        "source": inquiry.utm_source,
        "medium": inquiry.utm_medium,
        "campaign": inquiry.utm_campaign,
        "term": inquiry.utm_term,
    }
    print(f"[ENDPOINT][INQUIRY] Meritto payload: {meritto_payload}")

    asyncio.create_task(
        meritto_service.send_inquiry_to_crm(**meritto_payload)
    )
    
    return {"message": "Inquiry submitted successfully", "id": new_inquiry.id}


@router.post("/{college_slug}/contact", status_code=status.HTTP_201_CREATED)
async def submit_contact(
    college_slug: str,
    contact: ContactCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a new contact form with address information
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
    
    new_contact = Contact(
        college_slug=college.slug,
        name=contact.name,
        email=contact.email,
        phone_no=contact.phone_no,
        state=contact.state,
        city=contact.city,
        address=contact.address,
        message=contact.message
    )
    
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    
    print(f"[ENDPOINT] New contact created - ID: {new_contact.id}, Email: {contact.email}")
    
    # Send to Meritto CRM in parallel (non-blocking)
    asyncio.create_task(
        meritto_service.send_contact_to_crm(
            contact_id=new_contact.id,
            name=contact.name,
            email=contact.email,
            phone_no=contact.phone_no,
            state=contact.state,
            city=contact.city,
            address=contact.address,
            message=contact.message,
            college_name=college.name,
            c_course=contact.c_course,
            c_specialization=contact.c_specialization,
            source=contact.utm_source,
            medium=contact.utm_medium,
            campaign=contact.utm_campaign,
            term=contact.utm_term,
        )
    )
    
    return {"message": "Contact form submitted successfully", "id": new_contact.id}


# ============= ACTIVITIES PUBLIC API =============
@router.get("/{college_slug}/activities", response_model=List[ActivityListItem])
async def list_activities_by_college(
    college_slug: str,
    activity_type: Optional[str] = Query(None, description="Filter by activity type: workshop, cultural, event_celebration"),
    db: Session = Depends(get_db)
):
    """
    List active activities for a college

    Example: GET /api/ipsa/activities
    Filter:  GET /api/ipsa/activities?activity_type=workshop
    """
    if activity_type == "events":
        activity_type = "event_celebration"
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()

    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    query = db.query(Activity).filter(
        Activity.college_id == college.id,
        Activity.is_active == True
    )

    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)

    items = query.order_by(
        (Activity.start_date == None).asc(),
        Activity.start_date.desc()
    ).all()

    return [
        ActivityListItem(
            id=a.id,
            activity_type=a.activity_type.value,
            title=a.title,
            slug=a.slug,
            short_description=a.short_description,
            main_image=a.main_image,
            start_date=a.start_date,
            end_date=a.end_date,
        )
        for a in items
    ]


@router.get("/{college_slug}/activities/{activity_id}", response_model=ActivityDetail)
async def get_activity_detail(
    college_slug: str,
    activity_id: int,
    db: Session = Depends(get_db)
):
    """
    Get activity detail by ID

    Example: GET /api/ipsa/activities/1
    """
    if activity_type == "events":
        activity_type = "event_celebration"
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    a = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.college_id == college.id
    ).first()
    if not a or not a.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

    return ActivityDetail(
        id=a.id,
        activity_type=a.activity_type.value,
        title=a.title,
        slug=a.slug,
        short_description=a.short_description,
        content_html=a.content_html,
        main_image=a.main_image,
        gallery_images=a.gallery_images,
        start_date=a.start_date,
        end_date=a.end_date,
        created_at=a.created_at,
    )


# ============= ALUMNI ENDPOINTS =============
@router.get("/{college_slug}/alumni", response_model=List[AlumniListItem])
async def list_alumni_by_college(
    college_slug: str,
    db: Session = Depends(get_db)
):
    """
    List active alumni members for a college

    Example: GET /api/ipsa/alumni
    """
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()

    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    alumni_list = db.query(Alumni).filter(
        Alumni.college_id == college.id,
        Alumni.is_active == True
    ).order_by(Alumni.created_at.desc()).all()

    return [
        AlumniListItem(
            id=a.id,
            name=a.name,
            achievement=a.achievement,
            main_image=a.main_image,
            is_active=a.is_active,
        )
        for a in alumni_list
    ]


@router.get("/{college_slug}/alumni/{alumni_id}", response_model=AlumniDetail)
async def get_alumni_detail(
    college_slug: str,
    alumni_id: int,
    db: Session = Depends(get_db)
):
    """
    Get alumni detail by ID

    Example: GET /api/ipsa/alumni/1
    """
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    a = db.query(Alumni).filter(
        Alumni.id == alumni_id,
        Alumni.college_id == college.id
    ).first()
    if not a or not a.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alumni not found")

    return AlumniDetail(
        id=a.id,
        name=a.name,
        achievement=a.achievement,
        description=a.description,
        main_image=a.main_image,
        gallery_images=a.gallery_images,
        videos=a.videos,
        created_at=a.created_at,
    )

@router.get("/{college_slug}/activities/slug/{activity_slug}", response_model=ActivityDetail)
async def get_activity_by_slug(
    college_slug: str,
    activity_slug: str,
    db: Session = Depends(get_db)
):
    """
    Get activity detail by slug

    Example: GET /api/ipsa/activities/slug/annual-cultural-fest
    """
    college = db.query(College).filter(
        College.slug == college_slug,
        College.is_active == True
    ).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"College '{college_slug}' not found")

    a = db.query(Activity).filter(
        Activity.slug == activity_slug,
        Activity.college_id == college.id
    ).first()
    if not a or not a.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

    return ActivityDetail(
        id=a.id,
        activity_type=a.activity_type.value,
        title=a.title,
        slug=a.slug,
        short_description=a.short_description,
        content_html=a.content_html,
        main_image=a.main_image,
        gallery_images=a.gallery_images,
        start_date=a.start_date,
        end_date=a.end_date,
        created_at=a.created_at,
    )


# ============= ALL COLLEGES WITH COURSES =============
@router.get("/public/colleges-with-courses", response_model=Dict[str, Any])
async def get_all_colleges_with_courses(db: Session = Depends(get_db)):
    """
    Returns all active colleges with their active course names.

    Example: GET /api/public/colleges-with-courses
    
    Returns:
    {
        "colleges": [
            {
                "name": "IBMR",
                "slug": "ibmr",
                "courses": ["BBA", "MBA", "Ph.D"]
            },
            {
                "name": "SOC",
                "slug": "soc",
                "courses": ["B.Sc", "BCA", "MCA", ...]
            },
            ...
        ]
    }
    """
    colleges = db.query(College).filter(College.is_active == True).all()
    
    colleges_data = []
    for college in colleges:
        courses = db.query(Course).filter(
            Course.college_id == college.id,
            Course.is_active == True
        ).all()
        
        course_names = [course.name for course in courses]
        
        colleges_data.append({
            "name": college.name,
            "slug": college.slug,
            "courses": course_names
        })
    
    return {
        "colleges": colleges_data
    }
