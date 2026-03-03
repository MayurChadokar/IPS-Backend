from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, File, UploadFile, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.models import User, College, Page, Section, SectionContent, Faculty, Course, Inquiry, Contact, Activity, ActivityType, News, Event, Alumni, SocialMediaLink
from datetime import timedelta, datetime
from typing import Optional
import json
from pathlib import Path
from typing import List, Dict, Any
from app.core.cloudinary import upload_image
from app.core.cloudinary import delete_image, get_public_id_from_url
from fastapi import Body
from fastapi.responses import JSONResponse


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
    
    inquiries_count = db.query(Inquiry).count()
    contacts_count = db.query(Contact).count()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": current_user,
        "colleges_count": colleges_count,
        "pages_count": pages_count,
        "sections_count": sections_count,
        "inquiries_count": inquiries_count,
        "contacts_count": contacts_count
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
    footer_logo: UploadFile = File(None),
    document_download_link: str = Form(""),
    domain: str = Form(""),
    is_active: bool = Form(True),
    social_media_data: str = Form("[]"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create new college"""
    logo_path = None
    footer_logo_path = None
    
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
    
    # Handle footer logo upload
    if footer_logo and footer_logo.filename:
        try:
            footer_logo_path = upload_image(footer_logo.file, folder="college_logos")
        except Exception as e:
            return templates.TemplateResponse("admin/colleges/form.html", {
                "request": request,
                "user": current_user,
                "college": None,
                "action": "Create",
                "error": f"Footer logo upload failed: {str(e)}"
            })
    
    college = College(
        name=name,
        slug=slug,
        logo=logo_path,
        footer_logo=footer_logo_path,
        document_download_link=document_download_link if document_download_link else None,
        domain=domain if domain else None,
        is_active=is_active
    )
    
    try:
        db.add(college)
        db.flush()  # Flush to get college ID
        
        # Add social media links
        try:
            social_data = json.loads(social_media_data)
            for item in social_data:
                if item.get('platform') and item.get('url'):
                    social_link = SocialMediaLink(
                        college_id=college.id,
                        platform=item['platform'],
                        url=item['url'],
                        is_active=True,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(social_link)
        except (json.JSONDecodeError, KeyError):
            pass
        
        db.commit()
        return RedirectResponse(url="/admin/colleges", status_code=303)
    except Exception as e:
        db.rollback()
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
    footer_logo: UploadFile = File(None),
    document_download_link: str = Form(""),
    domain: str = Form(""),
    is_active: bool = Form(True),
    social_media_data: str = Form("[]"),
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
    
    # Handle footer logo upload if new file provided
    if footer_logo and footer_logo.filename:
        try:
            college.footer_logo = upload_image(footer_logo.file, folder="college_logos")
        except Exception as e:
            return templates.TemplateResponse("admin/colleges/form.html", {
                "request": request,
                "user": current_user,
                "college": college,
                "action": "Edit",
                "error": f"Footer logo upload failed: {str(e)}"
            })
    
    college.name = name
    college.slug = slug
    college.document_download_link = document_download_link if document_download_link else None
    college.domain = domain if domain else None
    college.is_active = is_active
    
    try:
        # Delete existing social media links
        db.query(SocialMediaLink).filter(SocialMediaLink.college_id == college_id).delete()
        
        # Add new social media links
        try:
            social_data = json.loads(social_media_data)
            for item in social_data:
                if item.get('platform') and item.get('url'):
                    social_link = SocialMediaLink(
                        college_id=college_id,
                        platform=item['platform'],
                        url=item['url'],
                        is_active=True,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(social_link)
        except (json.JSONDecodeError, KeyError):
            pass
        
        db.commit()
        return RedirectResponse(url="/admin/colleges", status_code=303)
    except Exception as e:
        db.rollback()
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


# ============= ACTIVITIES MANAGEMENT =============
@router.get("/colleges/{college_id}/activities", response_class=HTMLResponse)
async def list_activities_page(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List activities for a college"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    activities = db.query(Activity).filter(Activity.college_id == college_id).order_by(Activity.start_date.desc()).all()

    return templates.TemplateResponse("admin/activities/list.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "activities": activities
    })


@router.get("/colleges/{college_id}/activities/new", response_class=HTMLResponse)
async def create_activity_form(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create activity form"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    return templates.TemplateResponse("admin/activities/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "activity": None,
        "action": "Create",
        "activity_types": ActivityType
    })


# ============= NEWS MANAGEMENT =============
@router.get("/colleges/{college_id}/news", response_class=HTMLResponse)
async def list_news_page(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    news_list = db.query(News).filter(News.college_id == college_id).order_by(News.published_at.desc()).all()

    return templates.TemplateResponse("admin/news/list.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "news_list": news_list
    })


@router.get("/colleges/{college_id}/news/new", response_class=HTMLResponse)
async def create_news_form(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    return templates.TemplateResponse("admin/news/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "news": None,
        "action": "Create"
    })


@router.post("/colleges/{college_id}/news/new")
async def create_news(
    request: Request,
    college_id: int,
    title: str = Form(...),
    subtitle: str = Form(""),
    content_html: str = Form(""),
    thumbnail_image: UploadFile = File(None),
    gallery_images: List[UploadFile] = File(None),
    short_description: str = Form(""),
    is_published: bool = Form(False),
    published_at: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    thumb_path = None
    if thumbnail_image and thumbnail_image.filename:
        try:
            thumb_path = upload_image(thumbnail_image.file, folder="news_thumbs")
        except Exception as e:
            return templates.TemplateResponse("admin/news/form.html", {
                "request": request,
                "user": current_user,
                "college": college,
                "news": None,
                "action": "Create",
                "error": f"Thumbnail upload failed: {str(e)}"
            })

    gallery_paths = []
    if gallery_images:
        for img in gallery_images:
            if img and img.filename:
                try:
                    path = upload_image(img.file, folder="news_gallery")
                    gallery_paths.append(path)
                except Exception as e:
                    return templates.TemplateResponse("admin/news/form.html", {
                        "request": request,
                        "user": current_user,
                        "college": college,
                        "news": None,
                        "action": "Create",
                        "error": f"Gallery image upload failed: {str(e)}"
                    })

    n = News(
        college_id=college.id,
        title=title,
        subtitle=subtitle or None,
        content_html=content_html,
        thumbnail_image=thumb_path,
        short_description=short_description or None,
        gallery_images=gallery_paths if gallery_paths else None,
        is_published=is_published,
        published_at=(datetime.fromisoformat(published_at) if published_at else None)
    )

    db.add(n)
    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{college.id}/news", status_code=303)


@router.get("/news/{news_id}/edit", response_class=HTMLResponse)
async def edit_news_form(
    request: Request,
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    n = db.query(News).filter(News.id == news_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="News not found")

    college = db.query(College).filter(College.id == n.college_id).first()

    return templates.TemplateResponse("admin/news/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "news": n,
        "action": "Edit"
    })


@router.post("/news/{news_id}/edit")
async def update_news(
    request: Request,
    news_id: int,
    title: str = Form(...),
    subtitle: str = Form(""),
    content_html: str = Form(""),
    thumbnail_image: UploadFile = File(None),
    remove_thumbnail_image: bool = Form(False),
    gallery_images: List[UploadFile] = File(None),
    remove_gallery_images: str = Form(""),
    short_description: str = Form(""),
    is_published: bool = Form(False),
    published_at: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    n = db.query(News).filter(News.id == news_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="News not found")

    # Handle thumbnail replacement/removal
    if remove_thumbnail_image and n.thumbnail_image:
        try:
            delete_image(get_public_id_from_url(n.thumbnail_image))
        except Exception:
            pass
        n.thumbnail_image = None

    if thumbnail_image and thumbnail_image.filename:
        try:
            n.thumbnail_image = upload_image(thumbnail_image.file, folder="news_thumbs")
        except Exception as e:
            return templates.TemplateResponse("admin/news/form.html", {
                "request": request,
                "user": current_user,
                "college": db.query(College).filter(College.id == n.college_id).first(),
                "news": n,
                "action": "Edit",
                "error": f"Thumbnail upload failed: {str(e)}"
            })

    # Handle gallery images removal
    if remove_gallery_images:
        removed_urls = [url.strip() for url in remove_gallery_images.split(',') if url.strip()]
        if n.gallery_images:
            n.gallery_images = [img for img in n.gallery_images if img not in removed_urls]
        # Delete from cloud storage
        for url in removed_urls:
            try:
                delete_image(get_public_id_from_url(url))
            except Exception:
                pass

    # Handle gallery images upload
    if gallery_images and gallery_images[0].filename:
        gallery_paths = list(n.gallery_images) if n.gallery_images else []
        for img in gallery_images:
            if img and img.filename:
                try:
                    path = upload_image(img.file, folder="news_gallery")
                    gallery_paths.append(path)
                except Exception as e:
                    return templates.TemplateResponse("admin/news/form.html", {
                        "request": request,
                        "user": current_user,
                        "college": db.query(College).filter(College.id == n.college_id).first(),
                        "news": n,
                        "action": "Edit",
                        "error": f"Gallery image upload failed: {str(e)}"
                    })
        n.gallery_images = gallery_paths if gallery_paths else None

    n.title = title
    n.subtitle = subtitle or None
    n.content_html = content_html
    n.short_description = short_description or None
    n.is_published = is_published
    n.published_at = (datetime.fromisoformat(published_at) if published_at else None)

    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{n.college_id}/news", status_code=303)


@router.post("/news/{news_id}/delete")
async def delete_news(news_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    n = db.query(News).filter(News.id == news_id).first()
    if n:
        # delete thumbnail from cloud
        if n.thumbnail_image:
            try:
                delete_image(get_public_id_from_url(n.thumbnail_image))
            except Exception:
                pass
        db.delete(n)
        db.commit()

    return RedirectResponse(url=f"/admin/colleges/{n.college_id if n else ''}/news", status_code=303)


# ============= EVENTS MANAGEMENT =============
@router.get("/colleges/{college_id}/events", response_class=HTMLResponse)
async def list_events_page(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    events = db.query(Event).filter(Event.college_id == college_id).order_by(Event.start_date.desc()).all()

    return templates.TemplateResponse("admin/events/list.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "events": events
    })


@router.get("/colleges/{college_id}/events/new", response_class=HTMLResponse)
async def create_event_form(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    return templates.TemplateResponse("admin/events/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "event": None,
        "action": "Create"
    })


# Upload endpoint for rich editor images
@router.post("/uploads/image")
async def upload_editor_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Upload image used by rich text editors (TinyMCE). Returns JSON with `location`."""
    try:
        print(f"Uploading editor image via Cloudinary for user={current_user.id}, filename={file.filename}")
        url = upload_image(file.file, folder="editor_images")
        print(f"Upload successful: {url}")
        # Return multiple common keys so various TinyMCE upload flows accept the URL
        return JSONResponse({
            "location": url,
            "src": url,
            "url": url
        })
    except Exception as e:
        print(f"Editor upload error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Upload endpoint for rich editor PDFs (saved locally, served via /uploads static mount)
@router.post("/uploads/pdf")
async def upload_editor_pdf(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    """Upload a PDF file – saves to local uploads/pdfs/ directory and returns a public URL."""
    import uuid, shutil

    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return JSONResponse({"error": "Only PDF files are allowed"}, status_code=400)

    try:
        # Create pdfs sub-directory inside uploads/
        pdf_dir = UPLOAD_DIR / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)

        # Use UUID prefix to avoid collisions
        safe_name = f"{uuid.uuid4().hex}_{file.filename}"
        dest = pdf_dir / safe_name

        with dest.open("wb") as out_file:
            shutil.copyfileobj(file.file, out_file)

        # Build the public URL using the request base URL
        base_url = str(request.base_url).rstrip("/")
        url = f"{base_url}/uploads/pdfs/{safe_name}"

        print(f"PDF saved locally: {dest} → {url}")
        return JSONResponse({"location": url, "src": url, "url": url})

    except Exception as e:
        print(f"PDF upload error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/colleges/{college_id}/events/new")
async def create_event(
    request: Request,
    college_id: int,
    title: str = Form(...),
    subtitle: str = Form(""),
    content_html: str = Form(""),
    thumbnail_image: UploadFile = File(None),
    short_description: str = Form(""),
    location: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    thumb = None
    if thumbnail_image and thumbnail_image.filename:
        try:
            thumb = upload_image(thumbnail_image.file, folder="event_thumbs")
        except Exception as e:
            return templates.TemplateResponse("admin/events/form.html", {
                "request": request,
                "user": current_user,
                "college": college,
                "event": None,
                "action": "Create",
                "error": f"Thumbnail upload failed: {str(e)}"
            })

    ev = Event(
        college_id=college.id,
        title=title,
        subtitle=subtitle or None,
        content_html=content_html,
        thumbnail_image=thumb,
        short_description=short_description or None,
        location=location or None,
        start_date=(datetime.fromisoformat(start_date) if start_date else None),
        end_date=(datetime.fromisoformat(end_date) if end_date else None),
        is_active=is_active
    )

    db.add(ev)
    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{college.id}/events", status_code=303)


@router.get("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_form(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    college = db.query(College).filter(College.id == ev.college_id).first()

    return templates.TemplateResponse("admin/events/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "event": ev,
        "action": "Edit"
    })


@router.post("/events/{event_id}/edit")
async def update_event(
    request: Request,
    event_id: int,
    title: str = Form(...),
    subtitle: str = Form(""),
    content_html: str = Form(""),
    thumbnail_image: UploadFile = File(None),
    remove_thumbnail_image: bool = Form(False),
    short_description: str = Form(""),
    location: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    if remove_thumbnail_image and ev.thumbnail_image:
        try:
            delete_image(get_public_id_from_url(ev.thumbnail_image))
        except Exception:
            pass
        ev.thumbnail_image = None

    if thumbnail_image and thumbnail_image.filename:
        try:
            ev.thumbnail_image = upload_image(thumbnail_image.file, folder="event_thumbs")
        except Exception as e:
            return templates.TemplateResponse("admin/events/form.html", {
                "request": request,
                "user": current_user,
                "college": db.query(College).filter(College.id == ev.college_id).first(),
                "event": ev,
                "action": "Edit",
                "error": f"Thumbnail upload failed: {str(e)}"
            })

    ev.title = title
    ev.subtitle = subtitle or None
    ev.content_html = content_html
    ev.short_description = short_description or None
    ev.location = location or None
    ev.start_date = (datetime.fromisoformat(start_date) if start_date else None)
    ev.end_date = (datetime.fromisoformat(end_date) if end_date else None)
    ev.is_active = is_active

    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{ev.college_id}/events", status_code=303)


@router.post("/events/{event_id}/delete")
async def delete_event(event_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if ev:
        if ev.thumbnail_image:
            try:
                delete_image(get_public_id_from_url(ev.thumbnail_image))
            except Exception:
                pass
        db.delete(ev)
        db.commit()

    return RedirectResponse(url=f"/admin/colleges/{ev.college_id if ev else ''}/events", status_code=303)


@router.post("/colleges/{college_id}/activities/new")
async def create_activity(
    request: Request,
    college_id: int,
    activity_type: str = Form(...),
    title: str = Form(...),
    slug: str = Form(""),
    short_description: str = Form(""),
    content_html: str = Form(""),
    main_image: UploadFile = File(None),
    gallery_media_files: List[UploadFile] = File(None),
    start_date: str = Form(""),
    end_date: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create new activity"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    # Auto-generate slug from title if not provided
    import re
    activity_slug = slug.strip() if slug else None
    if not activity_slug:
        activity_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

    main_image_url = None
    gallery_urls = []

    try:
        if main_image and main_image.filename:
            main_image_url = upload_image(main_image.file, folder=f"activities/{college_id}", convert_to_webp=True, quality=80)

        if gallery_media_files:
            for f in gallery_media_files:
                if f and f.filename:
                    url = upload_image(f.file, folder=f"activities/{college_id}", convert_to_webp=True, quality=80)
                    gallery_urls.append(url)
    except Exception as e:
        return templates.TemplateResponse("admin/activities/form.html", {
            "request": request,
            "user": current_user,
            "college": college,
            "activity": None,
            "action": "Create",
            "error": f"Upload failed: {str(e)}",
            "activity_types": ActivityType
        })

    # Parse dates
    sd = None
    ed = None
    try:
        if start_date:
            sd = datetime.fromisoformat(start_date)
        if end_date:
            ed = datetime.fromisoformat(end_date)
    except Exception:
        sd = None
        ed = None

    activity = Activity(
        college_id=college_id,
        activity_type=ActivityType(activity_type),
        title=title,
        slug=activity_slug,
        short_description=short_description if short_description else None,
        content_html=content_html if content_html else None,
        main_image=main_image_url,
        gallery_images=gallery_urls if gallery_urls else None,
        start_date=sd,
        end_date=ed,
        is_active=is_active
    )

    db.add(activity)
    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{college_id}/activities", status_code=303)


@router.get("/activities/{activity_id}/edit", response_class=HTMLResponse)
async def edit_activity_form(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Edit activity form"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    return templates.TemplateResponse("admin/activities/form.html", {
        "request": request,
        "user": current_user,
        "college": activity.college,
        "activity": activity,
        "action": "Edit",
        "activity_types": ActivityType
    })


@router.post("/activities/{activity_id}/edit")
async def update_activity(
    request: Request,
    activity_id: int,
    activity_type: str = Form(...),
    title: str = Form(...),
    slug: str = Form(""),
    short_description: str = Form(""),
    content_html: str = Form(""),
    main_image: UploadFile = File(None),
    gallery_media_files: List[UploadFile] = File(None),
    retain_gallery: List[str] = Form(None),
    remove_main_image: str = Form(None),
    start_date: str = Form(""),
    end_date: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update existing activity"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    try:
        # Handle main image removal
        if remove_main_image:
            if activity.main_image:
                try:
                    delete_image(get_public_id_from_url(activity.main_image))
                except Exception:
                    pass
            activity.main_image = None

        # Handle new main image upload
        if main_image and main_image.filename:
            activity.main_image = upload_image(main_image.file, folder=f"activities/{activity.college_id}", convert_to_webp=True, quality=80)

        # Start with retained gallery images if provided, otherwise keep existing
        if retain_gallery is not None:
            gallery_urls = list(retain_gallery)
        else:
            gallery_urls = activity.gallery_images or []

        # Append newly uploaded gallery images
        if gallery_media_files:
            for f in gallery_media_files:
                if f and f.filename:
                    url = upload_image(f.file, folder=f"activities/{activity.college_id}", convert_to_webp=True, quality=80)
                    gallery_urls.append(url)

        activity.gallery_images = gallery_urls
    except Exception as e:
        return templates.TemplateResponse("admin/activities/form.html", {
            "request": request,
            "user": current_user,
            "college": activity.college,
            "activity": activity,
            "action": "Edit",
            "error": f"Upload failed: {str(e)}",
            "activity_types": ActivityType
        })

    # Parse dates
    try:
        activity.start_date = datetime.fromisoformat(start_date) if start_date else None
    except Exception:
        activity.start_date = None
    try:
        activity.end_date = datetime.fromisoformat(end_date) if end_date else None
    except Exception:
        activity.end_date = None

    # Update slug
    import re
    activity_slug = slug.strip() if slug else None
    if not activity_slug:
        activity_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    activity.slug = activity_slug

    activity.activity_type = ActivityType(activity_type)
    activity.title = title
    activity.short_description = short_description if short_description else None
    activity.content_html = content_html if content_html else None
    activity.is_active = is_active

    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{activity.college_id}/activities", status_code=303)


@router.post("/activities/{activity_id}/delete")
async def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete activity"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if activity:
        college_id = activity.college_id
        db.delete(activity)
        db.commit()
        return RedirectResponse(url=f"/admin/colleges/{college_id}/activities", status_code=303)

    return RedirectResponse(url="/admin/colleges", status_code=303)



@router.post("/activities/{activity_id}/image/remove-main")
async def remove_activity_main_image(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Remove main image from activity and delete from Cloudinary if possible"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        return JSONResponse({"success": False, "message": "Activity not found"}, status_code=404)

    if not activity.main_image:
        return JSONResponse({"success": False, "message": "No main image set"}, status_code=400)

    public_id = get_public_id_from_url(activity.main_image)
    if public_id:
        try:
            delete_image(public_id)
        except Exception:
            # continue even if delete fails
            pass

    activity.main_image = None
    db.commit()

    return JSONResponse({"success": True})


@router.post("/activities/{activity_id}/image/remove-gallery")
async def remove_activity_gallery_image(
    activity_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Remove a gallery image (by URL) from activity and delete from Cloudinary if possible"""
    image_url = payload.get("image_url")
    if not image_url:
        return JSONResponse({"success": False, "message": "image_url required"}, status_code=400)

    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        return JSONResponse({"success": False, "message": "Activity not found"}, status_code=404)

    gallery = activity.gallery_images or []
    if image_url not in gallery:
        return JSONResponse({"success": False, "message": "Image not found in gallery"}, status_code=404)

    public_id = get_public_id_from_url(image_url)
    if public_id:
        try:
            delete_image(public_id)
        except Exception:
            pass

    # remove from list
    new_gallery = [g for g in gallery if g != image_url]
    activity.gallery_images = new_gallery
    db.commit()

    return JSONResponse({"success": True})


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
    meta_title: str = Form(""),
    meta_keywords: str = Form(""),
    canonical_url: str = Form(""),
    robots: str = Form(""),
    og_title: str = Form(""),
    og_description: str = Form(""),
    og_image: str = Form(""),
    twitter_title: str = Form(""),
    twitter_description: str = Form(""),
    twitter_image: str = Form(""),
    schema_markup: str = Form(""),
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
        meta_title=meta_title if meta_title else None,
        meta_keywords=meta_keywords if meta_keywords else None,
        canonical_url=canonical_url if canonical_url else None,
        robots=robots if robots else "index, follow",
        og_title=og_title if og_title else None,
        og_description=og_description if og_description else None,
        og_image=og_image if og_image else None,
        twitter_title=twitter_title if twitter_title else None,
        twitter_description=twitter_description if twitter_description else None,
        twitter_image=twitter_image if twitter_image else None,
        schema_markup=schema_markup if schema_markup else None,
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



@router.get("/pages/{page_id}/clone", response_class=HTMLResponse)
async def clone_page_form(
    request: Request,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Show clone form to copy a page into another college"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # List colleges except current
    colleges = db.query(College).filter(College.id != page.college_id).all()

    # Build a map of college_id -> list of existing pages for duplicate detection
    college_pages_map = {}
    for c in colleges:
        college_pages_map[c.id] = [
            {"title": p.title, "slug": p.slug, "is_active": p.is_active}
            for p in c.pages
        ]

    return templates.TemplateResponse("admin/pages/clone.html", {
        "request": request,
        "user": current_user,
        "page": page,
        "colleges": colleges,
        "college_pages_map": json.dumps(college_pages_map)
    })


@router.post("/pages/{page_id}/clone")
async def clone_page(
    request: Request,
    page_id: int,
    target_college_ids: List[int] = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Clone a page and its sections/content into multiple colleges"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    for target_college_id in target_college_ids:
        target_college = db.query(College).filter(College.id == target_college_id).first()
        if not target_college:
            continue

        # Clone page fields
        new_page = Page(
            college_id=target_college.id,
            slug=page.slug,
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
            is_active=page.is_active
        )

        db.add(new_page)
        db.flush()

        # Clone sections and contents
        for section in page.sections:
            new_section = Section(
                college_id=target_college.id,
                page_id=new_page.id,
                section_key=section.section_key,
                section_type=section.section_type,
                sort_order=section.sort_order,
                is_active=section.is_active
            )
            db.add(new_section)
            db.flush()

            if section.content:
                new_content = SectionContent(
                    section_id=new_section.id,
                    content_json=section.content.content_json
                )
                db.add(new_content)

    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{page.college_id}/pages", status_code=303)


@router.post("/pages/{page_id}/edit")
async def update_page(
    request: Request,
    page_id: int,
    slug: str = Form(...),
    title: str = Form(...),
    meta_description: str = Form(""),
    meta_title: str = Form(""),
    meta_keywords: str = Form(""),
    canonical_url: str = Form(""),
    robots: str = Form(""),
    og_title: str = Form(""),
    og_description: str = Form(""),
    og_image: str = Form(""),
    twitter_title: str = Form(""),
    twitter_description: str = Form(""),
    twitter_image: str = Form(""),
    schema_markup: str = Form(""),
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
    page.meta_title = meta_title if meta_title else None
    page.meta_keywords = meta_keywords if meta_keywords else None
    page.canonical_url = canonical_url if canonical_url else None
    page.robots = robots if robots else "index, follow"
    page.og_title = og_title if og_title else None
    page.og_description = og_description if og_description else None
    page.og_image = og_image if og_image else None
    page.twitter_title = twitter_title if twitter_title else None
    page.twitter_description = twitter_description if twitter_description else None
    page.twitter_image = twitter_image if twitter_image else None
    page.schema_markup = schema_markup if schema_markup else None
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
    testimonials_media_files: List[UploadFile] = File(None),
    split_media_file: UploadFile = File(None),
    images_logo_files: List[UploadFile] = File(None),
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

        elif section_type == 'testimonials' and testimonials_media_files:
            for file in testimonials_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in items array
            if 'items' in content_data:
                upload_index = 0
                for item in content_data['items']:
                    if 'image' in item and item['image'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            item['image'] = uploaded_files[upload_index]
                            upload_index += 1

        elif section_type == 'images_with_logo' and images_logo_files:
            # Upload each logo file and replace __UPLOAD__ placeholders in items
            for file in images_logo_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)

            if 'items' in content_data:
                upload_index = 0
                for it in content_data['items']:
                    if 'logo' in it and isinstance(it['logo'], str) and it['logo'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            it['logo'] = uploaded_files[upload_index]
                            upload_index += 1
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
    testimonials_media_files: List[UploadFile] = File(None),
    split_media_file: UploadFile = File(None),
    images_logo_files: List[UploadFile] = File(None),
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

        elif section_type == 'testimonials' and testimonials_media_files:
            for file in testimonials_media_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)
            
            # Replace __UPLOAD__ placeholders in items array
            if 'items' in content_data:
                upload_index = 0
                for item in content_data['items']:
                    if 'image' in item and item['image'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            item['image'] = uploaded_files[upload_index]
                            upload_index += 1
        elif section_type == 'images_with_logo' and images_logo_files:
            # Upload each logo file and replace placeholders in items
            for file in images_logo_files:
                if file and file.filename:
                    url = upload_image(file.file, folder=f"sections/{section_key}")
                    uploaded_files.append(url)

            if 'items' in content_data:
                upload_index = 0
                for it in content_data['items']:
                    if 'logo' in it and isinstance(it['logo'], str) and it['logo'].startswith('__UPLOAD__'):
                        if upload_index < len(uploaded_files):
                            it['logo'] = uploaded_files[upload_index]
                            upload_index += 1
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
    description: str = Form(""),
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
        description=description if description else None,
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
    description: str = Form(""),
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
    faculty.description = description if description else None
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


@router.get("/inquiries", response_class=HTMLResponse)
async def list_inquiries_page(
    request: Request,
    college_id: Optional[str] = Query(None),
    is_read: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all inquiries with filters and pagination"""
    query = db.query(Inquiry)
    
    # Parse filters manually to handle empty strings from form
    parsed_college_id = None
    if college_id and college_id.strip():
        try:
            parsed_college_id = int(college_id)
            query = query.filter(Inquiry.college_id == parsed_college_id)
        except ValueError:
            pass
            
    parsed_is_read = None
    if is_read == "true":
        parsed_is_read = True
        query = query.filter(Inquiry.is_read == True)
    elif is_read == "false":
        parsed_is_read = False
        query = query.filter(Inquiry.is_read == False)
        
    total_count = query.count()
    inquiries = query.order_by(Inquiry.created_at.desc())\
        .offset((page - 1) * limit)\
        .limit(limit)\
        .all()
    
    colleges = db.query(College).all()
    
    # Add IST time to each inquiry
    for inquiry in inquiries:
        if inquiry.created_at:
            inquiry.ist_date = inquiry.created_at + timedelta(hours=5, minutes=30)
    
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    return templates.TemplateResponse("admin/inquiries/list.html", {
        "request": request,
        "user": current_user,
        "inquiries": inquiries,
        "colleges": colleges,
        "college_id": parsed_college_id,
        "is_read": parsed_is_read,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "total_count": total_count
    })


@router.get("/inquiries/{inquiry_id}", response_class=HTMLResponse)
async def view_inquiry(
    request: Request,
    inquiry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """View inquiry details"""
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
        
    return templates.TemplateResponse("admin/inquiries/detail.html", {
        "request": request,
        "user": current_user,
        "inquiry": inquiry
    })


@router.post("/inquiries/{inquiry_id}/update")
async def update_inquiry(
    inquiry_id: int,
    is_read: bool = Form(False),
    admin_notes: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update inquiry status and notes"""
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    inquiry.is_read = is_read
    inquiry.admin_notes = admin_notes if admin_notes else None
    
    db.commit()
    
    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


@router.post("/inquiries/{inquiry_id}/delete")
async def delete_inquiry(
    inquiry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete an inquiry"""
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if inquiry:
        db.delete(inquiry)
        db.commit()
    
    return RedirectResponse(url="/admin/inquiries", status_code=303)


# ========== CONTACTS MANAGEMENT ==========
@router.get("/contacts", response_class=HTMLResponse)
async def list_contacts(
    request: Request,
    college_slug: Optional[str] = Query(None),
    read_status: Optional[str] = Query(None),
    page: int = Query(1),
    limit: int = Query(20),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all contacts with filters"""
    query = db.query(Contact)
    
    # Filter by college slug
    if college_slug:
        query = query.filter(Contact.college_slug == college_slug)
    
    # Filter by read status
    if read_status == "read":
        query = query.filter(Contact.read_status == True)
    elif read_status == "unread":
        query = query.filter(Contact.read_status == False)
    
    total_count = query.count()
    
    contacts = query\
        .order_by(Contact.created_at.desc())\
        .offset((page - 1) * limit)\
        .limit(limit)\
        .all()
    
    colleges = db.query(College).all()
    
    # Add IST time to each contact
    for contact in contacts:
        if contact.created_at:
            contact.ist_date = contact.created_at + timedelta(hours=5, minutes=30)
    
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    return templates.TemplateResponse("admin/contacts/list.html", {
        "request": request,
        "user": current_user,
        "contacts": contacts,
        "colleges": colleges,
        "college_slug": college_slug,
        "read_status": read_status,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "total_count": total_count
    })


@router.get("/contacts/{contact_id}", response_class=HTMLResponse)
async def view_contact(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """View contact details"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Mark as read when viewing
    if not contact.read_status:
        contact.read_status = True
        db.commit()
        
    return templates.TemplateResponse("admin/contacts/detail.html", {
        "request": request,
        "user": current_user,
        "contact": contact
    })


@router.post("/contacts/{contact_id}/update")
async def update_contact(
    contact_id: int,
    read_status: bool = Form(False),
    admin_note: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update contact status and notes"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    contact.read_status = read_status
    contact.admin_note = admin_note if admin_note else None
    
    db.commit()
    
    return RedirectResponse(url=f"/admin/contacts/{contact_id}", status_code=303)


@router.post("/contacts/{contact_id}/delete")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact:
        db.delete(contact)
        db.commit()
    
    return RedirectResponse(url="/admin/contacts", status_code=303)


# ============= ALUMNI MANAGEMENT =============
@router.get("/colleges/{college_id}/alumni", response_class=HTMLResponse)
async def list_alumni_page(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List alumni for a college"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    alumni_list = db.query(Alumni).filter(Alumni.college_id == college_id).order_by(Alumni.created_at.desc()).all()

    return templates.TemplateResponse("admin/alumni/list.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "alumni_list": alumni_list
    })


@router.get("/colleges/{college_id}/alumni/new", response_class=HTMLResponse)
async def create_alumni_form(
    request: Request,
    college_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create alumni form"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    return templates.TemplateResponse("admin/alumni/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "alumni": None,
        "action": "Create"
    })


@router.post("/colleges/{college_id}/alumni/new")
async def create_alumni(
    request: Request,
    college_id: int,
    name: str = Form(...),
    achievement: str = Form(""),
    description: str = Form(""),
    main_image: UploadFile = File(None),
    gallery_images: list = File(None),
    video_files: list = File(None),
    video_links: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create new alumni member"""
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    main_image_path = None
    if main_image and main_image.filename:
        try:
            main_image_path = upload_image(main_image.file, folder="alumni")
        except Exception as e:
            return templates.TemplateResponse("admin/alumni/form.html", {
                "request": request,
                "user": current_user,
                "college": college,
                "alumni": None,
                "action": "Create",
                "error": f"Image upload failed: {str(e)}"
            })

    # Handle gallery images
    gallery_images_list = []
    if gallery_images:
        if not isinstance(gallery_images, list):
            gallery_images = [gallery_images]
        
        for img in gallery_images:
            if img and img.filename:
                try:
                    img_path = upload_image(img.file, folder="alumni_gallery")
                    gallery_images_list.append(img_path)
                except Exception as e:
                    return templates.TemplateResponse("admin/alumni/form.html", {
                        "request": request,
                        "user": current_user,
                        "college": college,
                        "alumni": None,
                        "action": "Create",
                        "error": f"Gallery image upload failed: {str(e)}"
                    })

    # Handle video files and links
    videos_list = []
    
    # Process uploaded video files
    if video_files:
        if not isinstance(video_files, list):
            video_files = [video_files]
        
        for video in video_files:
            if video and video.filename:
                try:
                    video_path = upload_image(video.file, folder="alumni_videos")
                    videos_list.append(video_path)
                except Exception as e:
                    return templates.TemplateResponse("admin/alumni/form.html", {
                        "request": request,
                        "user": current_user,
                        "college": college,
                        "alumni": None,
                        "action": "Create",
                        "error": f"Video upload failed: {str(e)}"
                    })

    # Process video links
    if video_links:
        video_urls = [url.strip() for url in video_links.split('\n') if url.strip()]
        videos_list.extend(video_urls)

    alumni = Alumni(
        college_id=college.id,
        name=name,
        achievement=achievement or None,
        description=description or None,
        main_image=main_image_path,
        gallery_images=gallery_images_list if gallery_images_list else None,
        videos=videos_list if videos_list else None
    )

    db.add(alumni)
    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{college.id}/alumni", status_code=303)


@router.get("/alumni/{alumni_id}/edit", response_class=HTMLResponse)
async def edit_alumni_form(
    request: Request,
    alumni_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Edit alumni form"""
    alumni = db.query(Alumni).filter(Alumni.id == alumni_id).first()
    if not alumni:
        raise HTTPException(status_code=404, detail="Alumni not found")

    college = db.query(College).filter(College.id == alumni.college_id).first()

    return templates.TemplateResponse("admin/alumni/form.html", {
        "request": request,
        "user": current_user,
        "college": college,
        "alumni": alumni,
        "action": "Edit"
    })


@router.post("/alumni/{alumni_id}/edit")
async def update_alumni(
    request: Request,
    alumni_id: int,
    name: str = Form(...),
    achievement: str = Form(""),
    description: str = Form(""),
    main_image: UploadFile = File(None),
    gallery_images: list = File(None),
    video_files: list = File(None),
    video_links: str = Form(""),
    delete_gallery_images: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update alumni member"""
    alumni = db.query(Alumni).filter(Alumni.id == alumni_id).first()
    if not alumni:
        raise HTTPException(status_code=404, detail="Alumni not found")

    college = db.query(College).filter(College.id == alumni.college_id).first()

    # Handle main image upload
    if main_image and main_image.filename:
        try:
            # Delete old image if exists
            if alumni.main_image:
                delete_image(alumni.main_image)
            alumni.main_image = upload_image(main_image.file, folder="alumni")
        except Exception as e:
            return templates.TemplateResponse("admin/alumni/form.html", {
                "request": request,
                "user": current_user,
                "college": college,
                "alumni": alumni,
                "action": "Edit",
                "error": f"Image upload failed: {str(e)}"
            })

    # Handle deleted gallery images
    if delete_gallery_images:
        try:
            deleted_urls = json.loads(delete_gallery_images)
            if alumni.gallery_images:
                # Remove deleted images from array
                alumni.gallery_images = [img for img in alumni.gallery_images if img not in deleted_urls]
                # Delete from Cloudinary
                for img_url in deleted_urls:
                    try:
                        delete_image(img_url)
                    except:
                        pass
        except:
            pass

    # Handle gallery images - append to existing ones
    if gallery_images:
        if not isinstance(gallery_images, list):
            gallery_images = [gallery_images]
        
        # Initialize if None
        if not alumni.gallery_images:
            alumni.gallery_images = []
        
        for img in gallery_images:
            if img and img.filename:
                try:
                    img_path = upload_image(img.file, folder="alumni_gallery")
                    alumni.gallery_images.append(img_path)
                except Exception as e:
                    return templates.TemplateResponse("admin/alumni/form.html", {
                        "request": request,
                        "user": current_user,
                        "college": college,
                        "alumni": alumni,
                        "action": "Edit",
                        "error": f"Gallery image upload failed: {str(e)}"
                    })

    # Handle videos - replace with new ones (both files and links)
    videos_list = []
    
    # Process uploaded video files
    if video_files:
        if not isinstance(video_files, list):
            video_files = [video_files]
        
        for video in video_files:
            if video and video.filename:
                try:
                    video_path = upload_image(video.file, folder="alumni_videos")
                    videos_list.append(video_path)
                except Exception as e:
                    return templates.TemplateResponse("admin/alumni/form.html", {
                        "request": request,
                        "user": current_user,
                        "college": college,
                        "alumni": alumni,
                        "action": "Edit",
                        "error": f"Video upload failed: {str(e)}"
                    })

    # Process video links
    if video_links:
        video_urls = [url.strip() for url in video_links.split('\n') if url.strip()]
        videos_list.extend(video_urls)

    # Update videos only if new ones were provided
    if videos_list:
        alumni.videos = videos_list
    elif not video_files and not video_links:
        # If nothing provided, keep existing
        pass

    alumni.name = name
    alumni.achievement = achievement or None
    alumni.description = description or None

    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{college.id}/alumni", status_code=303)


@router.post("/alumni/{alumni_id}/delete")
async def delete_alumni(
    alumni_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete alumni member"""
    alumni = db.query(Alumni).filter(Alumni.id == alumni_id).first()
    if not alumni:
        raise HTTPException(status_code=404, detail="Alumni not found")

    college_id = alumni.college_id

    # Delete main image if exists
    if alumni.main_image:
        try:
            delete_image(alumni.main_image)
        except:
            pass

    db.delete(alumni)
    db.commit()

    return RedirectResponse(url=f"/admin/colleges/{college_id}/alumni", status_code=303)

