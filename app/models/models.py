from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(enum.Enum):
    """User roles for authentication"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    EDITOR = "editor"


class User(Base):
    """
    Admin/User table for authentication
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.ADMIN, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class College(Base):
    """
    Main tenant table - each college is a separate tenant
    """
    __tablename__ = "colleges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    logo = Column(String(500), nullable=True)
    domain = Column(String(255), nullable=True, unique=True)  # For domain mapping
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    pages = relationship("Page", back_populates="college", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="college", cascade="all, delete-orphan")
    faculties = relationship("Faculty", back_populates="college", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="college", cascade="all, delete-orphan")
    inquiries = relationship("Inquiry", back_populates="college", cascade="all, delete-orphan")


class Page(Base):
    """
    Pages for each college (Home, About, Contact, etc.)
    Same slug can exist for different colleges
    """
    __tablename__ = "pages"
    
    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    slug = Column(String(100), nullable=False, index=True)  # home, about-us, contact
    title = Column(String(255), nullable=False)
    meta_description = Column(Text, nullable=True)
    meta_title = Column(String(255), nullable=True)  # <title> tag
    meta_keywords = Column(Text, nullable=True)

    # Advanced SEO
    canonical_url = Column(String(500), nullable=True)
    robots = Column(String(100), default="index, follow")  # noindex, nofollow

    # Open Graph (Social Sharing)
    og_title = Column(String(255), nullable=True)
    og_description = Column(Text, nullable=True)
    og_image = Column(String(500), nullable=True)

    # Twitter Cards
    twitter_title = Column(String(255), nullable=True)
    twitter_description = Column(Text, nullable=True)
    twitter_image = Column(String(500), nullable=True)

    # Structured Data (Schema JSON-LD)
    schema_markup = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    college = relationship("College", back_populates="pages")
    sections = relationship("Section", back_populates="page", cascade="all, delete-orphan")
    
    # Composite unique constraint
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class Section(Base):
    """
    Sections within pages (Hero, Stats, Accordion, etc.)
    """
    __tablename__ = "sections"
    
    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    section_key = Column(String(100), nullable=False)  # hero, why_ipsa, stats, accordion
    section_type = Column(String(50), nullable=False)  # hero, text, stats, accordion, image
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    college = relationship("College", back_populates="sections")
    page = relationship("Page", back_populates="sections")
    content = relationship("SectionContent", back_populates="section", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class SectionContent(Base):
    """
    JSON-driven content for each section
    """
    __tablename__ = "section_contents"
    
    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), unique=True, nullable=False)
    content_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    section = relationship("Section", back_populates="content")
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class PageTemplate(Base):
    """
    Optional: Templates for quick page creation
    """
    __tablename__ = "page_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_key = Column(String(100), unique=True, nullable=False)  # default_home, default_about
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    template_json = Column(JSON, nullable=False)  # Contains sections structure
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class Faculty(Base):
    """
    Faculty/Staff members for each college
    """
    __tablename__ = "faculties"
    
    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    contact = Column(String(20), nullable=True)
    image = Column(String(500), nullable=True)  # Profile photo URL
    designation = Column(String(255), nullable=True)  # Professor, Assistant Professor, etc.
    department = Column(String(255), nullable=True)  # Computer Science, Management, etc.
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    college = relationship("College", back_populates="faculties")
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class Course(Base):
    """
    Courses offered by each college
    """
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # MBA, BBA, B.Tech, etc.
    description = Column(Text, nullable=True)
    eligibility = Column(Text, nullable=True)  # Eligibility criteria
    fee_structure = Column(JSON, nullable=True)  # JSON for flexible fee structure
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    college = relationship("College", back_populates="courses")
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class Inquiry(Base):
    """
    Inquiries/Leads from contact forms
    """
    __tablename__ = "inquiries"
    
    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    course_interested = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    college = relationship("College", back_populates="inquiries")
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )
