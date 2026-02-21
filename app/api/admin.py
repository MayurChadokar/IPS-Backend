from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.security import get_current_active_admin, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from app.models.models import UserRole
from app.models.models import College, Page, Section, SectionContent, PageTemplate, User, Faculty, Course
from app.schemas.schemas import (
    CollegeCreate, CollegeUpdate, CollegeResponse,
    PageCreate, PageUpdate, PageResponse,
    SectionCreate, SectionUpdate, SectionResponse,
    FacultyCreate, FacultyUpdate, FacultyResponse,
    CourseCreate, CourseUpdate, CourseResponse,
    ClonePageRequest, CreateCollegeFromTemplate
)
from typing import List, Dict, Any
from app.core.cloudinary import upload_image


router = APIRouter()


# ============= COLLEGE MANAGEMENT =============
@router.post("/colleges", response_model=CollegeResponse, status_code=status.HTTP_201_CREATED)
async def create_college(
    college: CollegeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Create a new college"""
    db_college = College(**college.model_dump())
    try:
        db.add(db_college)
        db.commit()
        db.refresh(db_college)
        return db_college
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"College with slug '{college.slug}' already exists"
        )


@router.get("/colleges", response_model=List[CollegeResponse])
async def list_colleges(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all colleges"""
    colleges = db.query(College).offset(skip).limit(limit).all()
    return colleges


@router.get("/colleges/{college_id}", response_model=CollegeResponse)
async def get_college(college_id: int, db: Session = Depends(get_db)):
    """Get college by ID"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found"
        )
    return college


@router.put("/colleges/{college_id}", response_model=CollegeResponse)
async def update_college(
    college_id: int,
    college_update: CollegeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Update college"""
    db_college = db.query(College).filter(College.id == college_id).first()
    if not db_college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found"
        )
    
    update_data = college_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_college, field, value)
    
    db.commit()
    db.refresh(db_college)
    return db_college


@router.delete("/colleges/{college_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_college(
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Delete college (cascades to all pages and sections)"""
    db_college = db.query(College).filter(College.id == college_id).first()
    if not db_college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found"
        )
    
    db.delete(db_college)
    db.commit()
    return None


# ============= PAGE MANAGEMENT =============
@router.post("/pages", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    page: PageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Create a new page for a college"""
    # Verify college exists
    college = db.query(College).filter(College.id == page.college_id).first()
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found"
        )
    
    db_page = Page(**page.model_dump())
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return db_page


@router.get("/colleges/{college_id}/pages", response_model=List[PageResponse])
async def list_pages_by_college_id(
    college_id: int,
    db: Session = Depends(get_db)
):
    """List all pages for a college"""
    pages = db.query(Page).filter(Page.college_id == college_id).all()
    return pages


@router.get("/pages/{page_id}", response_model=PageResponse)
async def get_page(page_id: int, db: Session = Depends(get_db)):
    """Get page by ID"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    return page


@router.put("/pages/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: int,
    page_update: PageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Update page"""
    db_page = db.query(Page).filter(Page.id == page_id).first()
    if not db_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    update_data = page_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_page, field, value)
    
    db.commit()
    db.refresh(db_page)
    return db_page


@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Delete page (cascades to all sections)"""
    db_page = db.query(Page).filter(Page.id == page_id).first()
    if not db_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    db.delete(db_page)
    db.commit()
    return None


# ============= SECTION MANAGEMENT =============
@router.post("/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    section: SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Create a new section with content"""
    # Verify page exists
    page = db.query(Page).filter(Page.id == section.page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    # Extract content_json
    content_json = section.content_json
    section_data = section.model_dump(exclude={'content_json'})
    
    # Create section
    db_section = Section(**section_data)
    db.add(db_section)
    db.flush()  # Get the section ID
    
    # Create content
    db_content = SectionContent(
        section_id=db_section.id,
        content_json=content_json
    )
    db.add(db_content)
    
    db.commit()
    db.refresh(db_section)
    return db_section


@router.get("/pages/{page_id}/sections", response_model=List[SectionResponse])
async def list_sections_by_page(page_id: int, db: Session = Depends(get_db)):
    """List all sections for a page"""
    sections = db.query(Section).filter(
        Section.page_id == page_id
    ).order_by(Section.sort_order).all()
    return sections


@router.get("/sections/{section_id}", response_model=SectionResponse)
async def get_section(section_id: int, db: Session = Depends(get_db)):
    """Get section by ID"""
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    return section


@router.put("/sections/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: int,
    section_update: SectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Update section and/or its content"""
    db_section = db.query(Section).filter(Section.id == section_id).first()
    if not db_section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    update_data = section_update.model_dump(exclude_unset=True)
    
    # Handle content_json separately
    if 'content_json' in update_data:
        content_json = update_data.pop('content_json')
        if db_section.content:
            db_section.content.content_json = content_json
        else:
            db_content = SectionContent(
                section_id=db_section.id,
                content_json=content_json
            )
            db.add(db_content)
    
    # Update section fields
    for field, value in update_data.items():
        setattr(db_section, field, value)
    
    db.commit()
    db.refresh(db_section)
    return db_section


@router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Delete section (cascades to content)"""
    db_section = db.query(Section).filter(Section.id == section_id).first()
    if not db_section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    db.delete(db_section)
    db.commit()
    return None



# ============= FACULTY MANAGEMENT =============
@router.post("/faculties", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
async def create_faculty(
    faculty: FacultyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Create a new faculty member"""
    # Verify college exists
    college = db.query(College).filter(College.id == faculty.college_id).first()
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found"
        )
    
    db_faculty = Faculty(**faculty.model_dump())
    db.add(db_faculty)
    db.commit()
    db.refresh(db_faculty)
    return db_faculty


@router.get("/colleges/{college_id}/faculties", response_model=List[FacultyResponse])
async def list_faculties_by_college(college_id: int, db: Session = Depends(get_db)):
    """List all faculty members for a college"""
    faculties = db.query(Faculty).filter(Faculty.college_id == college_id).all()
    return faculties


@router.get("/faculties/{faculty_id}", response_model=FacultyResponse)
async def get_faculty(faculty_id: int, db: Session = Depends(get_db)):
    """Get faculty by ID"""
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    return faculty


@router.put("/faculties/{faculty_id}", response_model=FacultyResponse)
async def update_faculty(
    faculty_id: int,
    faculty_update: FacultyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Update faculty member"""
    db_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not db_faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    update_data = faculty_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_faculty, field, value)
    
    db.commit()
    db.refresh(db_faculty)
    return db_faculty


@router.delete("/faculties/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Delete faculty member"""
    db_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not db_faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    db.delete(db_faculty)
    db.commit()
    return None


# ============= COURSE MANAGEMENT =============
@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Create a new course"""
    # Verify college exists
    college = db.query(College).filter(College.id == course.college_id).first()
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found"
        )
    
    db_course = Course(**course.model_dump())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/colleges/{college_id}/courses", response_model=List[CourseResponse])
async def list_courses_by_college(college_id: int, db: Session = Depends(get_db)):
    """List all courses for a college"""
    courses = db.query(Course).filter(Course.college_id == college_id).all()
    return courses


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(course_id: int, db: Session = Depends(get_db)):
    """Get course by ID"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return course


@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Update course"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    update_data = course_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Delete course"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    db.delete(db_course)
    db.commit()
    return None


# ============= BULK OPERATIONS =============
@router.post("/pages/clone", response_model=PageResponse)
async def clone_page(
    request: ClonePageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    Clone a page from one college to another
    Useful for creating similar pages across colleges
    """
    # Get source college and page
    source_college = db.query(College).filter(
        College.slug == request.source_college_slug
    ).first()
    if not source_college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source college '{request.source_college_slug}' not found"
        )
    
    source_page = db.query(Page).filter(
        Page.college_id == source_college.id,
        Page.slug == request.source_page_slug
    ).first()
    if not source_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source page '{request.source_page_slug}' not found"
        )
    
    # Get target college
    target_college = db.query(College).filter(
        College.slug == request.target_college_slug
    ).first()
    if not target_college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target college '{request.target_college_slug}' not found"
        )
    
    # Create new page
    new_page = Page(
        college_id=target_college.id,
        slug=source_page.slug,
        title=request.new_page_title or source_page.title,
        meta_description=source_page.meta_description,
        is_active=source_page.is_active
    )
    db.add(new_page)
    db.flush()
    
    # Clone all sections
    source_sections = db.query(Section).filter(
        Section.page_id == source_page.id
    ).all()
    
    for source_section in source_sections:
        new_section = Section(
            college_id=target_college.id,
            page_id=new_page.id,
            section_key=source_section.section_key,
            section_type=source_section.section_type,
            sort_order=source_section.sort_order,
            is_active=source_section.is_active
        )
        db.add(new_section)
        db.flush()
        
        # Clone content
        if source_section.content:
            new_content = SectionContent(
                section_id=new_section.id,
                content_json=source_section.content.content_json
            )
            db.add(new_content)
    
    db.commit()
    db.refresh(new_page)
    return new_page


@router.post("/upload", response_model=Dict[str, Any])
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder: str = "general",
    db: Session = Depends(get_db)
):
    """
    Upload a file to Cloudinary
    Returns the secure URL
    """
    # Authenticate: accept Bearer token OR session cookie (admin_session)
    token = None
    auth_header = request.headers.get('authorization')
    if auth_header and auth_header.lower().startswith('bearer '):
        token = auth_header.split(None, 1)[1]
    else:
        token = request.cookies.get('admin_session')

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get('sub')
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        url = upload_image(file.file, folder=folder)
        return {"url": url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
