from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.models import User, College, Page, Section, SectionContent
from datetime import timedelta
from typing import Optional
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Session cookie name
SESSION_COOKIE_NAME = "admin_session"


def get_current_admin_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current admin from session cookie"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    
    try:
        from jose import jwt
        from app.core.security import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active:
            return user
    except:
        return None
    
    return None


# ============= LOGIN PAGE =============
@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    return templates.TemplateResponse("admin/login.html", {
        "request": request
    })


@router.post("/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle admin login"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": "Invalid username or password"
        }, status_code=400)
    
    if not user.is_active:
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": "Account is inactive"
        }, status_code=400)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(hours=8)
    )
    
    # Redirect to dashboard
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(key=SESSION_COOKIE_NAME, value=access_token, httponly=True, max_age=28800)
    return response


@router.get("/logout")
async def admin_logout():
    """Logout admin"""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


# ============= DASHBOARD =============
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Admin dashboard"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get stats
    colleges_count = db.query(College).count()
    pages_count = db.query(Page).count()
    sections_count = db.query(Section).count()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": current_user,
        "colleges_count": colleges_count,
        "pages_count": pages_count,
        "sections_count": sections_count
    })


# ============= COLLEGES MANAGEMENT =============
@router.get("/colleges", response_class=HTMLResponse)
async def list_colleges_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """List all colleges"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    colleges = db.query(College).all()
    return templates.TemplateResponse("admin/colleges/list.html", {
        "request": request,
        "user": current_user,
        "colleges": colleges
    })


@router.get("/colleges/new", response_class=HTMLResponse)
async def create_college_page(
    request: Request,
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Create new college form"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    return templates.TemplateResponse("admin/colleges/form.html", {
        "request": request,
        "user": current_user,
        "college": None,
        "action": "Create"
    })


@router.post("/colleges/new")
async def create_college(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    logo: str = Form(""),
    domain: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Create new college"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    college = College(
        name=name,
        slug=slug,
        logo=logo if logo else None,
        domain=domain if domain else None,
        is_active=is_active
    )
    
    try:
        db.add(college)
        db.commit()
        return RedirectResponse(url="/admin/colleges", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("admin/colleges/form.html", {
            "request": request,
            "user": current_user,
            "college": None,
            "action": "Create",
            "error": f"Error creating college: {str(e)}"
        })


@router.get("/colleges/{college_id}/edit", response_class=HTMLResponse)
async def edit_college_page(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Edit college form"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    return templates.TemplateResponse("admin/colleges/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "action": "Edit"
    })


@router.post("/colleges/{college_id}/edit")
async def update_college(
    request: Request,
    college_id: int,
    name: str = Form(...),
    slug: str = Form(...),
    logo: str = Form(""),
    domain: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Update college"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    college.name = name
    college.slug = slug
    college.logo = logo if logo else None
    college.domain = domain if domain else None
    college.is_active = is_active
    
    try:
        db.commit()
        return RedirectResponse(url="/admin/colleges", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("admin/colleges/form.html", {
            "request": request,
            "user": current_user,
            "college": college,
            "action": "Edit",
            "error": f"Error updating college: {str(e)}"
        })


@router.post("/colleges/{college_id}/delete")
async def delete_college(
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Delete college"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    college = db.query(College).filter(College.id == college_id).first()
    if college:
        db.delete(college)
        db.commit()
    
    return RedirectResponse(url="/admin/colleges", status_code=303)


# ============= PAGES MANAGEMENT =============
@router.get("/colleges/{college_id}/pages", response_class=HTMLResponse)
async def list_pages_page(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """List pages for a college"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    pages = db.query(Page).filter(Page.college_id == college_id).all()
    
    return templates.TemplateResponse("admin/pages/list.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "pages": pages
    })


@router.get("/colleges/{college_id}/pages/new", response_class=HTMLResponse)
async def create_page_form(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Create page form"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    return templates.TemplateResponse("admin/pages/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "page": None,
        "action": "Create"
    })


@router.post("/colleges/{college_id}/pages/new")
async def create_page(
    request: Request,
    college_id: int,
    slug: str = Form(...),
    title: str = Form(...),
    meta_description: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Create new page"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    page = Page(
        college_id=college_id,
        slug=slug,
        title=title,
        meta_description=meta_description if meta_description else None,
        is_active=is_active
    )
    
    db.add(page)
    db.commit()
    
    return RedirectResponse(url=f"/admin/colleges/{college_id}/pages", status_code=303)


@router.get("/pages/{page_id}/edit", response_class=HTMLResponse)
async def edit_page_form(
    request: Request,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Edit page form"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return templates.TemplateResponse("admin/pages/form.html", {
        "request": request,
        "user": current_user,
        "college": page.college,
        "page": page,
        "action": "Edit"
    })


@router.post("/pages/{page_id}/edit")
async def update_page(
    request: Request,
    page_id: int,
    slug: str = Form(...),
    title: str = Form(...),
    meta_description: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Update page"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    page.slug = slug
    page.title = title
    page.meta_description = meta_description if meta_description else None
    page.is_active = is_active
    
    db.commit()
    
    return RedirectResponse(url=f"/admin/colleges/{page.college_id}/pages", status_code=303)


@router.post("/pages/{page_id}/delete")
async def delete_page(
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Delete page"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    page = db.query(Page).filter(Page.id == page_id).first()
    if page:
        college_id = page.college_id
        db.delete(page)
        db.commit()
        return RedirectResponse(url=f"/admin/colleges/{college_id}/pages", status_code=303)
    
    return RedirectResponse(url="/admin/colleges", status_code=303)


# ============= SECTIONS MANAGEMENT =============
@router.get("/pages/{page_id}/sections", response_class=HTMLResponse)
async def list_sections_page(
    request: Request,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """List sections for a page"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    sections = db.query(Section).filter(Section.page_id == page_id).order_by(Section.sort_order).all()
    
    return templates.TemplateResponse("admin/sections/list.html", {
        "request": request,
        "user": current_user,
        "page": page,
        "sections": sections
    })


@router.get("/pages/{page_id}/sections/new", response_class=HTMLResponse)
async def create_section_form(
    request: Request,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Create section form"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return templates.TemplateResponse("admin/sections/form.html", {
        "request": request,
        "user": current_user,
        "page": page,
        "section": None,
        "action": "Create"
    })


@router.post("/pages/{page_id}/sections/new")
async def create_section(
    request: Request,
    page_id: int,
    section_key: str = Form(...),
    section_type: str = Form(...),
    sort_order: int = Form(0),
    content_json: str = Form("{}"),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Create new section"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Parse JSON content
    try:
        content_data = json.loads(content_json)
    except:
        content_data = {}
    
    section = Section(
        college_id=page.college_id,
        page_id=page_id,
        section_key=section_key,
        section_type=section_type,
        sort_order=sort_order,
        is_active=is_active
    )
    
    db.add(section)
    db.flush()
    
    section_content = SectionContent(
        section_id=section.id,
        content_json=content_data
    )
    db.add(section_content)
    db.commit()
    
    return RedirectResponse(url=f"/admin/pages/{page_id}/sections", status_code=303)


@router.get("/sections/{section_id}/edit", response_class=HTMLResponse)
async def edit_section_form(
    request: Request,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Edit section form"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    return templates.TemplateResponse("admin/sections/form.html", {
        "request": request,
        "user": current_user,
        "page": section.page,
        "section": section,
        "action": "Edit"
    })


@router.post("/sections/{section_id}/edit")
async def update_section(
    request: Request,
    section_id: int,
    section_key: str = Form(...),
    section_type: str = Form(...),
    sort_order: int = Form(0),
    content_json: str = Form("{}"),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Update section"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    # Parse JSON content
    try:
        content_data = json.loads(content_json)
    except:
        content_data = {}
    
    section.section_key = section_key
    section.section_type = section_type
    section.sort_order = sort_order
    section.is_active = is_active
    
    if section.content:
        section.content.content_json = content_data
    else:
        section_content = SectionContent(
            section_id=section.id,
            content_json=content_data
        )
        db.add(section_content)
    
    db.commit()
    
    return RedirectResponse(url=f"/admin/pages/{section.page_id}/sections", status_code=303)


@router.post("/sections/{section_id}/delete")
async def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_from_cookie)
):
    """Delete section"""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    section = db.query(Section).filter(Section.id == section_id).first()
    if section:
        page_id = section.page_id
        db.delete(section)
        db.commit()
        return RedirectResponse(url=f"/admin/pages/{page_id}/sections", status_code=303)
    
    return RedirectResponse(url="/admin/colleges", status_code=303)
