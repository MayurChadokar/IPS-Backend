from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============= College Schemas =============
class CollegeBase(BaseModel):
    name: str
    slug: str
    logo: Optional[str] = None
    footer_logo: Optional[str] = None
    document_download_link: Optional[str] = None
    domain: Optional[str] = None
    is_active: bool = True


class CollegeCreate(CollegeBase):
    pass


class CollegeUpdate(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None
    footer_logo: Optional[str] = None
    document_download_link: Optional[str] = None
    domain: Optional[str] = None
    is_active: Optional[bool] = None


class CollegeResponse(CollegeBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============= Social Media Link Schemas =============
class SocialMediaLinkBase(BaseModel):
    platform: str
    url: str
    is_active: bool = True


class SocialMediaLinkCreate(SocialMediaLinkBase):
    college_id: int


class SocialMediaLinkUpdate(BaseModel):
    platform: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None


class SocialMediaLinkResponse(SocialMediaLinkBase):
    id: int
    college_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CollegeResponseWithSocial(CollegeResponse):
    """College response with social media links"""
    social_media_links: List[SocialMediaLinkResponse] = []


# ============= Page Schemas =============
class PageBase(BaseModel):
    slug: str
    title: str
    meta_description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_keywords: Optional[str] = None
    canonical_url: Optional[str] = None
    robots: Optional[str] = "index, follow"
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    twitter_title: Optional[str] = None
    twitter_description: Optional[str] = None
    twitter_image: Optional[str] = None
    schema_markup: Optional[str] = None
    is_active: bool = True


class PageCreate(PageBase):
    college_id: int


class PageUpdate(BaseModel):
    title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_keywords: Optional[str] = None
    canonical_url: Optional[str] = None
    robots: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    twitter_title: Optional[str] = None
    twitter_description: Optional[str] = None
    twitter_image: Optional[str] = None
    schema_markup: Optional[str] = None
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
    Includes all SEO metadata for frontend consumption
    """
    college: str  # slug
    page: str  # slug
    title: str
    meta_description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_keywords: Optional[str] = None
    canonical_url: Optional[str] = None
    robots: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    twitter_title: Optional[str] = None
    twitter_description: Optional[str] = None
    twitter_image: Optional[str] = None
    schema_markup: Optional[str] = None
    sections: Dict[str, Any]  # Keyed by section_key
    
    model_config = ConfigDict(from_attributes=True)


class CollegePublicInfo(BaseModel):
    """
    Response for college information and its pages
    """
    name: str
    slug: str
    logo: Optional[str] = None
    footer_logo: Optional[str] = None
    document_download_link: Optional[str] = None
    domain: Optional[str] = None
    pages: List[Dict[str, Any]]
    social_media_links: List[Dict[str, Any]] = []
    
    model_config = ConfigDict(from_attributes=True)


# ============= News & Events Public Schemas =============
class NewsListItem(BaseModel):
    id: int
    title: str
    subtitle: Optional[str] = None
    thumbnail_image: Optional[str] = None
    short_description: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NewsDetail(BaseModel):
    id: int
    title: str
    subtitle: Optional[str] = None
    content_html: str
    thumbnail_image: Optional[str] = None
    short_description: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EventListItem(BaseModel):
    id: int
    title: str
    subtitle: Optional[str] = None
    thumbnail_image: Optional[str] = None
    short_description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EventDetail(BaseModel):
    id: int
    title: str
    subtitle: Optional[str] = None
    content_html: str
    thumbnail_image: Optional[str] = None
    short_description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============= Activity Public Schemas =============
class ActivityListItem(BaseModel):
    id: int
    activity_type: str
    title: str
    slug: Optional[str] = None
    short_description: Optional[str] = None
    main_image: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ActivityDetail(BaseModel):
    id: int
    activity_type: str
    title: str
    slug: Optional[str] = None
    short_description: Optional[str] = None
    content_html: Optional[str] = None
    main_image: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============= Alumni Schemas =============
class AlumniBase(BaseModel):
    name: str
    achievement: Optional[str] = None
    description: Optional[str] = None
    main_image: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    is_active: bool = True


class AlumniCreate(AlumniBase):
    college_id: int


class AlumniUpdate(BaseModel):
    name: Optional[str] = None
    achievement: Optional[str] = None
    description: Optional[str] = None
    main_image: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AlumniResponse(AlumniBase):
    id: int
    college_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AlumniListItem(BaseModel):
    id: int
    name: str
    achievement: Optional[str] = None
    main_image: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AlumniDetail(BaseModel):
    id: int
    name: str
    achievement: Optional[str] = None
    description: Optional[str] = None
    main_image: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    created_at: Optional[datetime] = None

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
    state: Optional[str] = None
    city: Optional[str] = None
    course_interested: Optional[str] = None
    message: Optional[str] = None
    c_course: Optional[str] = None
    c_specialization: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None

# ============= Contact Schemas =============
class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone_no: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    message: Optional[str] = None
    c_course: Optional[str] = None
    c_specialization: Optional[str] = None


# ============= Journal & Volume Schemas =============
class JournalBase(BaseModel):
    name: str
    logo_url: Optional[str] = None
    home_html: Optional[str] = None
    about_html: Optional[str] = None
    call_for_papers_html: Optional[str] = None
    policies_html: Optional[str] = None
    author_guidelines_html: Optional[str] = None
    contact_us_html: Optional[str] = None
    is_active: bool = True

class JournalCreate(JournalBase):
    pass

class JournalUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    home_html: Optional[str] = None
    about_html: Optional[str] = None
    call_for_papers_html: Optional[str] = None
    policies_html: Optional[str] = None
    author_guidelines_html: Optional[str] = None
    contact_us_html: Optional[str] = None
    is_active: Optional[bool] = None

class JournalResponse(JournalBase):
    id: int
    college_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class PaperItem(BaseModel):
    title: str
    authors: str
    page_range: str
    pdf_link: Optional[str] = None

class JournalVolumeBase(BaseModel):
    volume_title: str
    editorial_link: Optional[str] = None
    contents_link: Optional[str] = None
    papers: Optional[List[PaperItem]] = None
    is_active: bool = True

class JournalVolumeCreate(JournalVolumeBase):
    journal_id: int

class JournalVolumeUpdate(BaseModel):
    volume_title: Optional[str] = None
    editorial_link: Optional[str] = None
    contents_link: Optional[str] = None
    papers: Optional[List[PaperItem]] = None
    is_active: Optional[bool] = None

class JournalVolumeResponse(JournalVolumeBase):
    id: int
    college_id: int
    journal_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class JournalVolumeSummary(BaseModel):
    id: int
    journal_id: int
    volume_title: str
    
    model_config = ConfigDict(from_attributes=True)
