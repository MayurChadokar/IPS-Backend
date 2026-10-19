"""Validated inputs and frontend responses for careers."""
from datetime import date, datetime
from typing import List, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.dates import india_today


def validate_link(value: str, allow_email: bool = True) -> str:
    if any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("URL must not contain whitespace or control characters")
    if "\\" in value:
        raise ValueError("URL must not contain backslashes")
    parsed = urlsplit(value)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return value
    if allow_email and parsed.scheme == "mailto" and "@" in parsed.path:
        return value
    if value.startswith("/") and not value.startswith("//"):
        return value
    raise ValueError("Use an http(s) URL, a site-relative path, or a mailto email link")


class CareerOpeningBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)

    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="Faculty Positions", min_length=1, max_length=100)
    job_type: str = Field(default="Full Time", min_length=1, max_length=100)
    location: str = Field(default="Indore", min_length=1, max_length=255)
    department: Optional[str] = Field(default=None, max_length=255)
    short_description: Optional[str] = Field(default=None, max_length=1000)
    description: str = Field(min_length=1, max_length=50000)
    qualifications: Optional[str] = Field(default=None, max_length=20000)
    apply_url: str = Field(min_length=1, max_length=1000)
    posted_date: date = Field(default_factory=india_today)
    closing_date: Optional[date] = None
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("apply_url")
    @classmethod
    def valid_apply_url(cls, value):
        return validate_link(value)


class CareerOpeningCreate(CareerOpeningBase):
    pass


class CareerOpeningUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    job_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, min_length=1, max_length=255)
    department: Optional[str] = Field(default=None, max_length=255)
    short_description: Optional[str] = Field(default=None, max_length=1000)
    description: Optional[str] = Field(default=None, min_length=1, max_length=50000)
    qualifications: Optional[str] = Field(default=None, max_length=20000)
    apply_url: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    posted_date: Optional[date] = None
    closing_date: Optional[date] = None
    sort_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("title", "category", "job_type", "location", "description", "apply_url", "posted_date", "sort_order", "is_active")
    @classmethod
    def required_when_supplied(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @field_validator("apply_url")
    @classmethod
    def valid_apply_url(cls, value):
        return validate_link(value)


class CareerOpeningResponse(CareerOpeningBase):
    id: int
    college_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class CareerOpeningList(BaseModel):
    items: List[CareerOpeningResponse]
    total: int
    page: int
    page_size: int


class CareerFilterOptions(BaseModel):
    categories: List[str]
    job_types: List[str]
    locations: List[str]


class CareerPageSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(default="Careers - IPS Academy", min_length=1, max_length=255)
    meta_description: str = Field(default="Build your career at IPS Academy. Explore current faculty, administration and support openings.", max_length=1000)
    hero_image: str = Field(default="", max_length=1000)
    hero_alt: str = Field(default="Build your career at IPS Academy", max_length=255)
    introduction_title: str = Field(default="Build Your Career at IPS Academy", min_length=1, max_length=255)
    introduction_description: str = Field(
        default="IPS Academy brings together a legacy of academic excellence, diverse disciplines and a strong commitment to shaping future-ready professionals. With a vibrant academic ecosystem and a focus on innovation, research and industry relevance, we create an environment where ideas take shape and expertise creates impact.",
        min_length=1, max_length=10000,
    )
    openings_title: str = Field(default="Current Openings", min_length=1, max_length=255)
    categories: List[str] = Field(default_factory=lambda: ["Faculty Positions", "Administration", "Support Staff"], min_length=1, max_length=50)
    job_types: List[str] = Field(default_factory=lambda: ["Full Time", "Part Time", "Contract", "Visiting Faculty"], min_length=1, max_length=50)
    is_active: bool = True

    @field_validator("hero_image")
    @classmethod
    def valid_hero_image(cls, value):
        return validate_link(value, allow_email=False) if value else value

    @field_validator("categories", "job_types")
    @classmethod
    def valid_options(cls, values):
        cleaned = []
        seen = set()
        for value in values:
            value = value.strip()
            if not value or len(value) > 100:
                raise ValueError("Each option must contain between 1 and 100 characters")
            if value.casefold() not in seen:
                cleaned.append(value)
                seen.add(value.casefold())
        return cleaned
