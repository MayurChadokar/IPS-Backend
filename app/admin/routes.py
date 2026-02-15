from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.models import User, College, Page, Section, SectionContent, Faculty, Course
from datetime import timedelta
from typing import Optional
import json
from pathlib import Path
from typing import List, Dict, Any
from app.core.cloudinary import upload_image


router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Session cookie name
SESSION_COOKIE_NAME = "admin_session"

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


async def get_current_admin_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current admin from session cookie"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    
    try:
        from jose import jwt
        from app.core.security import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        
        user_id = int(user_id_str)
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active:
            return user
    except Exception:
        return None
    
    return None


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """Require admin authentication - raises redirect if not authenticated"""
    user = None
    token = request.cookies.get(SESSION_COOKIE_NAME)
    
    if token:
        try:
            from jose import jwt
            from app.core.security import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id_str: str = payload.get("sub")
            if user_id_str:
                user_id = int(user_id_str)
                user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        except Exception:
            pass
    
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    
    return user


# ============= ROOT REDIRECT =============
@router.get("/")
async def admin_root(request: Request, db: Session = Depends(get_db)):
    """Redirect to dashboard if logged in, otherwise to login"""
    current_user = await get_current_admin_from_cookie(request, db)
    if current_user:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return RedirectResponse(url="/admin/login", status_code=303)


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
    # Allow login with either username or email
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": "Invalid username/email or password"
        }, status_code=400)
    
    if not user.is_active:
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": "Account is inactive"
        }, status_code=400)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(hours=8)
    )
    
    # Redirect to dashboard
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME, 
        value=access_token, 
        httponly=True, 
        max_age=28800,
        samesite="lax"
    )
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
    current_user: User = Depends(require_admin)
):
    """Admin dashboard"""
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
    current_user: User = Depends(require_admin)
):
    """List all colleges"""
    colleges = db.query(College).all()
    return templates.TemplateResponse("admin/colleges/list.html", {
        "request": request,
        "user": current_user,
        "colleges": colleges
    })


@router.get("/colleges/new", response_class=HTMLResponse)
async def create_college_page(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """Create new college form"""
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
    logo: UploadFile = File(None),
    domain: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create new college"""
    logo_path = None
    
    # Handle logo upload
    if logo and logo.filename:
        try:
            logo_path = upload_image(logo.file, folder="college_logos")
        except Exception as e:
            return templates.TemplateResponse("admin/colleges/form.html", {
                "request": request,
                "user": current_user,
                "college": None,
                "action": "Create",
                "error": f"Logo upload failed: {str(e)}"
            })
    
    college = College(
        name=name,
        slug=slug,
        logo=logo_path,
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
    current_user: User = Depends(require_admin)
):
    """Edit college form"""
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
    logo: UploadFile = File(None),
    domain: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update college"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    # Handle logo upload if new file provided
    if logo and logo.filename:
        try:
            college.logo = upload_image(logo.file, folder="college_logos")
        except Exception as e:
            return templates.TemplateResponse("admin/colleges/form.html", {
                "request": request,
                "user": current_user,
                "college": college,
                "action": "Edit",
                "error": f"Logo upload failed: {str(e)}"
            })
    
    college.name = name
    college.slug = slug
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
    current_user: User = Depends(require_admin)
):
    """Delete college"""
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
    current_user: User = Depends(require_admin)
):
    """List pages for a college"""
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
    current_user: User = Depends(require_admin)
):
    """Create page form"""
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
    current_user: User = Depends(require_admin)
):
    """Create new page"""
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
    current_user: User = Depends(require_admin)
):
    """Edit page form"""
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
    current_user: User = Depends(require_admin)
):
    """Update page"""
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
    current_user: User = Depends(require_admin)
):
    """Delete page"""
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
    current_user: User = Depends(require_admin)
):
    """List sections for a page"""
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
    current_user: User = Depends(require_admin)
):
    """Create section form"""
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
    hero_media_files: List[UploadFile] = File(None),
    text_media_file: UploadFile = File(None),
    gallery_media_files: List[UploadFile] = File(None),
    team_media_files: List[UploadFile] = File(None),
    cards_media_files: List[UploadFile] = File(None),
    facilities_media_files: List[UploadFile] = File(None),
    split_media_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create new section"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Parse JSON content
    try:
        content_data = json.loads(content_json)
    except:
        content_data = {}
    
    # Handle file uploads based on section type
    uploaded_files = []
    
    try:
        if section_type == 'hero' and hero_media_files:
            for file in hero_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in images array
            if 'images' in content_data:
                new_images = []
                upload_index = 0
                for img in content_data['images']:
                    if img.startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            new_images.append(uploaded_files[upload_index])
                            upload_index += 1
                    else:
                        new_images.append(img)
                content_data['images'] = new_images
        
        elif section_type == 'text' and text_media_file and text_media_file.filename:
            url = upload_image(text_media_file.file, folder=f"sections/{section_key}")
            if 'image' in content_data and content_data['image'].startswith('__UPLOAD__'):
                content_data['image'] = url
        
        elif section_type == 'gallery' and gallery_media_files:
            for file in gallery_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in images array
            if 'images' in content_data:
                new_images = []
                upload_index = 0
                for img in content_data['images']:
                    if img.startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            new_images.append(uploaded_files[upload_index])
                            upload_index += 1
                    else:
                        new_images.append(img)
                content_data['images'] = new_images
        
        elif section_type == 'team' and team_media_files:
            for file in team_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in members array
            if 'members' in content_data:
                upload_index = 0
                for member in content_data['members']:
                    if 'image' in member and member['image'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            member['image'] = uploaded_files[upload_index]
                            upload_index += 1
        
        elif section_type == 'cards' and cards_media_files:
            for file in cards_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in cards array
            if 'cards' in content_data:
                upload_index = 0
                for card in content_data['cards']:
                    if 'icon' in card and card['icon'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            card['icon'] = uploaded_files[upload_index]
                            upload_index += 1
        
        elif section_type == 'facilities' and facilities_media_files:
            for file in facilities_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in facilities array
            if 'facilities' in content_data:
                upload_index = 0
                for facility in content_data['facilities']:
                    if 'image' in facility and facility['image'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            facility['image'] = uploaded_files[upload_index]
                            upload_index += 1
        
        elif section_type == 'split' and split_media_file and split_media_file.filename:
            url = upload_image(split_media_file.file, folder=f"sections/{section_key}")
            if 'image' in content_data and content_data['image'].startswith('__UPLOAD__'):
                content_data['image'] = url
    except Exception as e:
        # Create a mock section object to preserve form state
        mock_section = {
            "section_key": section_key,
            "section_type": section_type,
            "sort_order": sort_order,
            "is_active": is_active,
            "content": {"content_json": content_data}
        }
        return templates.TemplateResponse("admin/sections/form.html", {
            "request": request,
            "user": current_user,
            "page": page,
            "section": mock_section,
            "action": "Create",
            "error": f"Upload failed: {str(e)}"
        })
    
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
    current_user: User = Depends(require_admin)
):
    """Edit section form"""
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
    hero_media_files: List[UploadFile] = File(None),
    text_media_file: UploadFile = File(None),
    gallery_media_files: List[UploadFile] = File(None),
    team_media_files: List[UploadFile] = File(None),
    cards_media_files: List[UploadFile] = File(None),
    facilities_media_files: List[UploadFile] = File(None),
    split_media_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update section"""
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    # Parse JSON content
    try:
        content_data = json.loads(content_json)
    except:
        content_data = {}
    
    # Handle file uploads based on section type
    uploaded_files = []
    
    try:
        if section_type == 'hero' and hero_media_files:
            for file in hero_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in images array
            if 'images' in content_data:
                new_images = []
                upload_index = 0
                for img in content_data['images']:
                    if img.startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            new_images.append(uploaded_files[upload_index])
                            upload_index += 1
                    else:
                        new_images.append(img)
                content_data['images'] = new_images
        
        elif section_type == 'text' and text_media_file and text_media_file.filename:
            url = upload_image(text_media_file.file, folder=f"sections/{section_key}")
            if 'image' in content_data and content_data['image'].startswith('__UPLOAD__'):
                content_data['image'] = url
        
        elif section_type == 'gallery' and gallery_media_files:
            for file in gallery_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in images array
            if 'images' in content_data:
                new_images = []
                upload_index = 0
                for img in content_data['images']:
                    if img.startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            new_images.append(uploaded_files[upload_index])
                            upload_index += 1
                    else:
                        new_images.append(img)
                content_data['images'] = new_images
        
        elif section_type == 'team' and team_media_files:
            for file in team_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in members array
            if 'members' in content_data:
                upload_index = 0
                for member in content_data['members']:
                    if 'image' in member and member['image'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            member['image'] = uploaded_files[upload_index]
                            upload_index += 1
        
        elif section_type == 'cards' and cards_media_files:
            for file in cards_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in cards array
            if 'cards' in content_data:
                upload_index = 0
                for card in content_data['cards']:
                    if 'icon' in card and card['icon'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            card['icon'] = uploaded_files[upload_index]
                            upload_index += 1
        
        elif section_type == 'facilities' and facilities_media_files:
            for file in facilities_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in facilities array
            if 'facilities' in content_data:
                upload_index = 0
                for facility in content_data['facilities']:
                    if 'image' in facility and facility['image'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            facility['image'] = uploaded_files[upload_index]
                            upload_index += 1
        
        elif section_type == 'split' and split_media_file and split_media_file.filename:
            url = upload_image(split_media_file.file, folder=f"sections/{section_key}")
            if 'image' in content_data and content_data['image'].startswith('__UPLOAD__'):
                content_data['image'] = url
    except Exception as e:
        # Update current section object with submitted data to preserve form state
        section.section_key = section_key
        section.section_type = section_type
        section.sort_order = sort_order
        section.is_active = is_active
        if not section.content:
            from app.models.models import SectionContent
            section.content = SectionContent(content_json=content_data)
        else:
            section.content.content_json = content_data
            
        return templates.TemplateResponse("admin/sections/form.html", {
            "request": request,
            "user": current_user,
            "page": section.page,
            "section": section,
            "action": "Edit",
            "error": f"Upload failed: {str(e)}"
        })
    
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
    current_user: User = Depends(require_admin)
):
    """Delete section"""
    section = db.query(Section).filter(Section.id == section_id).first()
    if section:
        page_id = section.page_id
        db.delete(section)
        db.commit()
        return RedirectResponse(url=f"/admin/pages/{page_id}/sections", status_code=303)
    
    return RedirectResponse(url="/admin/colleges", status_code=303)


# ============= FACULTY MANAGEMENT =============
@router.get("/colleges/{college_id}/faculties", response_class=HTMLResponse)
async def list_faculties_page(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List faculties for a college"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    faculties = db.query(Faculty).filter(Faculty.college_id == college_id).all()
    
    return templates.TemplateResponse("admin/faculties/list.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "faculties": faculties
    })


@router.get("/colleges/{college_id}/faculties/new", response_class=HTMLResponse)
async def create_faculty_form(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create faculty form"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    return templates.TemplateResponse("admin/faculties/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "faculty": None,
        "action": "Create"
    })


@router.post("/colleges/{college_id}/faculties/new")
async def create_faculty(
    request: Request,
    college_id: int,
    name: str = Form(...),
    email: str = Form(""),
    contact: str = Form(""),
    designation: str = Form(""),
    department: str = Form(""),
    image: UploadFile = File(None),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create new faculty"""
    image_path = None
    if image and image.filename:
        try:
            image_path = upload_image(image.file, folder="faculty")
        except Exception as e:
            college = db.query(College).filter(College.id == college_id).first()
            return templates.TemplateResponse("admin/faculties/form.html", {
                "request": request,
                "user": current_user,
                "college": college,
                "faculty": None,
                "action": "Create",
                "error": f"Image upload failed: {str(e)}"
            })
    
    faculty = Faculty(
        college_id=college_id,
        name=name,
        email=email if email else None,
        contact=contact if contact else None,
        designation=designation if designation else None,
        department=department if department else None,
        image=image_path,
        is_active=is_active
    )
    
    db.add(faculty)
    db.commit()
    
    return RedirectResponse(url=f"/admin/colleges/{college_id}/faculties", status_code=303)


@router.get("/faculties/{faculty_id}/edit", response_class=HTMLResponse)
async def edit_faculty_form(
    request: Request,
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Edit faculty form"""
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    
    return templates.TemplateResponse("admin/faculties/form.html", {
        "request": request,
        "user": current_user,
        "college": faculty.college,
        "faculty": faculty,
        "action": "Edit"
    })


@router.post("/faculties/{faculty_id}/edit")
async def update_faculty(
    request: Request,
    faculty_id: int,
    name: str = Form(...),
    email: str = Form(""),
    contact: str = Form(""),
    designation: str = Form(""),
    department: str = Form(""),
    image: UploadFile = File(None),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update faculty"""
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    
    # Handle image upload if provided
    if image and image.filename:
        try:
            faculty.image = upload_image(image.file, folder="faculty")
        except Exception as e:
            return templates.TemplateResponse("admin/faculties/form.html", {
                "request": request,
                "user": current_user,
                "college": faculty.college,
                "faculty": faculty,
                "action": "Edit",
                "error": f"Image upload failed: {str(e)}"
            })
    
    faculty.name = name
    faculty.email = email if email else None
    faculty.contact = contact if contact else None
    faculty.designation = designation if designation else None
    faculty.department = department if department else None
    faculty.is_active = is_active
    
    db.commit()
    
    return RedirectResponse(url=f"/admin/colleges/{faculty.college_id}/faculties", status_code=303)


@router.post("/faculties/{faculty_id}/delete")
async def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete faculty"""
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if faculty:
        college_id = faculty.college_id
        db.delete(faculty)
        db.commit()
        return RedirectResponse(url=f"/admin/colleges/{college_id}/faculties", status_code=303)
    
    return RedirectResponse(url="/admin/colleges", status_code=303)


# ============= COURSES MANAGEMENT =============
@router.get("/colleges/{college_id}/courses", response_class=HTMLResponse)
async def list_courses_page(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List courses for a college"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    courses = db.query(Course).filter(Course.college_id == college_id).all()
    
    return templates.TemplateResponse("admin/courses/list.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "courses": courses
    })


@router.get("/colleges/{college_id}/courses/new", response_class=HTMLResponse)
async def create_course_form(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create course form"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    return templates.TemplateResponse("admin/courses/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "course": None,
        "action": "Create"
    })


@router.post("/colleges/{college_id}/courses/new")
async def create_course(
    request: Request,
    college_id: int,
    name: str = Form(...),
    description: str = Form(""),
    eligibility: str = Form(""),
    fee_structure: str = Form("{}"),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create new course"""
    # Parse JSON fee structure
    try:
        fee_data = json.loads(fee_structure)
    except:
        fee_data = {}
        
    course = Course(
        college_id=college_id,
        name=name,
        description=description if description else None,
        eligibility=eligibility if eligibility else None,
        fee_structure=fee_data,
        is_active=is_active
    )
    
    db.add(course)
    db.commit()
    
    return RedirectResponse(url=f"/admin/colleges/{college_id}/courses", status_code=303)


@router.get("/courses/{course_id}/edit", response_class=HTMLResponse)
async def edit_course_form(
    request: Request,
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Edit course form"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return templates.TemplateResponse("admin/courses/form.html", {
        "request": request,
        "user": current_user,
        "college": course.college,
        "course": course,
        "action": "Edit"
    })


@router.post("/courses/{course_id}/edit")
async def update_course(
    request: Request,
    course_id: int,
    name: str = Form(...),
    description: str = Form(""),
    eligibility: str = Form(""),
    fee_structure: str = Form("{}"),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update course"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Parse JSON fee structure
    try:
        fee_data = json.loads(fee_structure)
    except:
        fee_data = {}
    
    course.name = name
    course.description = description if description else None
    course.eligibility = eligibility if eligibility else None
    course.fee_structure = fee_data
    course.is_active = is_active
    
    db.commit()
    
    return RedirectResponse(url=f"/admin/colleges/{course.college_id}/courses", status_code=303)


@router.post("/courses/{course_id}/delete")
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete course"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if course:
        college_id = course.college_id
        db.delete(course)
        db.commit()
        return RedirectResponse(url=f"/admin/colleges/{college_id}/courses", status_code=303)
    
    return RedirectResponse(url="/admin/colleges", status_code=303)

