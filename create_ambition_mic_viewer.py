"""Create or update the read-only Ambition MIC entries account."""

from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models.models import User, UserRole


EMAIL = settings.AMBITION_MIC_VIEWER_EMAIL.strip()
PASSWORD = settings.AMBITION_MIC_VIEWER_PASSWORD
USERNAME = settings.AMBITION_MIC_VIEWER_USERNAME.strip() or "ambition_mic_viewer"


def ensure_access_scope_column() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "access_scope" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN access_scope VARCHAR(50) NULL"))

    inspector = inspect(engine)
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_access_scope" not in indexes:
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX ix_users_access_scope ON users (access_scope)"))


def create_or_update_viewer() -> None:
    if not EMAIL or not PASSWORD:
        raise RuntimeError(
            "AMBITION_MIC_VIEWER_EMAIL and AMBITION_MIC_VIEWER_PASSWORD must be set in .env"
        )
    ensure_access_scope_column()
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == EMAIL)
            | (User.username == USERNAME)
            | (User.username == "admission_viewer")
        ).first()
        if user is None:
            user = User(email=EMAIL, username=USERNAME)
            db.add(user)

        user.email = EMAIL
        user.username = USERNAME
        user.full_name = "Ambition MIC Viewer"
        user.hashed_password = get_password_hash(PASSWORD)
        user.role = UserRole.ADMIN
        user.access_scope = "ambition_mic_read_only"
        user.is_active = True
        db.commit()
        print(f"Ambition MIC viewer ready: {EMAIL}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_or_update_viewer()
