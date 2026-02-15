from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============= College Schemas =============
class CollegeBase(BaseModel):
    name: str
    slug: str
    logo: Optional[str] = None
    domain: Optional[str] = None
    is_active: bool = True


class CollegeCreate(CollegeBase):
    pass


class CollegeUpdate(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None
    domain: Optional[str] = None
    is_active: Optional[bool] = None


class CollegeResponse(CollegeBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============= Page Schemas =============
class PageBase(BaseModel):
    slug: str
    title: str
    meta_description: Optional[str] = None
    is_active: bool = True


class PageCreate(PageBase):
    college_id: int


class PageUpdate(BaseModel):
    title: Optional[str] = None
    meta_description: Optional[str] = None
    is_active: Optional[bool] = None


class PageResponse(PageBase):
    id: int
    college_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============= Section Schemas =============
class SectionContentBase(BaseModel):
    content_json: Dict[str, Any]


class SectionContentCreate(SectionContentBase):
    pass


class SectionContentUpdate(SectionContentBase):
    pass


class SectionContentResponse(SectionContentBase):
    id: int
    section_id: int
    
    model_config = ConfigDict(from_attributes=True)


class SectionBase(BaseModel):
    section_key: str
    section_type: str
    sort_order: int = 0
    is_active: bool = True


class SectionCreate(SectionBase):
    college_id: int
    page_id: int
    content_json: Dict[str, Any]


class SectionUpdate(BaseModel):
    section_type: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    content_json: Optional[Dict[str, Any]] = None


class SectionResponse(SectionBase):
    id: int
    college_id: int
    page_id: int
    content: Optional[SectionContentResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============= Faculty Schemas =============
class FacultyBase(BaseModel):
    name: str
    email: Optional[str] = None
    contact: Optional[str] = None
    image: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class FacultyCreate(FacultyBase):
    college_id: int


class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    image: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FacultyResponse(FacultyBase):
    id: int
    college_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============= Course Schemas =============
class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    eligibility: Optional[str] = None
    fee_structure: Optional[Dict[str, Any]] = None
    is_active: bool = True


class CourseCreate(CourseBase):
    college_id: int


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    eligibility: Optional[str] = None
    fee_structure: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class CourseResponse(CourseBase):
    id: int
    college_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============= Public API Response (Frontend) =============
class SectionPublicResponse(BaseModel):
    """Simplified section response for public API"""
    section_key: str
    section_type: str
    sort_order: int
    content: Dict[str, Any]


class PagePublicResponse(BaseModel):
    """
    Response for public frontend API
    Example: GET /api/ipsa/pages/home
    """
    college: str  # slug
    page: str  # slug
    title: str
    meta_description: Optional[str] = None
    sections: Dict[str, Any]  # Keyed by section_key
    
    model_config = ConfigDict(from_attributes=True)


# ============= Template Schemas =============
class PageTemplateBase(BaseModel):
    template_key: str
    name: str
    description: Optional[str] = None
    template_json: Dict[str, Any]


class PageTemplateCreate(PageTemplateBase):
    pass


class PageTemplateResponse(PageTemplateBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============= Bulk Operations =============
class ClonePageRequest(BaseModel):
    """Clone a page from one college to another"""
    source_college_slug: str
    source_page_slug: str
    target_college_slug: str
    new_page_title: Optional[str] = None


class CreateCollegeFromTemplate(BaseModel):
    """Create new college with default pages"""
    name: str
    slug: str
    logo: Optional[str] = None
    domain: Optional[str] = None
    use_default_template: bool = True


# ============= Inquiry Schemas =============
class InquiryCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    course_interested: Optional[str] = None
    message: Optional[str] = None
