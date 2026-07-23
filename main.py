from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.api import public, admin, auth
from app.admin import routes as admin_ui
import os


# Hide documentation in production by default unless explicitly enabled
ENABLE_DOCS = os.environ.get("ENABLE_DOCS", "false").lower() == "true"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create upload directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(public.router, prefix=settings.API_V1_PREFIX, tags=["Public API"])
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin API (Protected)"])
app.include_router(admin_ui.router, prefix="/admin", tags=["Admin UI"])


def get_db():
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/r/{short_code}")
async def redirect_short_url(short_code: str, db = Depends(get_db)):
    from app.models.models import ShortURL

    url_mapping = db.query(ShortURL).filter(ShortURL.short_code == short_code).first()
    if not url_mapping:
        raise HTTPException(status_code=404, detail="Short URL not found")
        
    return RedirectResponse(url=url_mapping.original_url)



@app.get("/")
async def root():
    return RedirectResponse(url="/admin/login")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7777,
        reload=True
    )
