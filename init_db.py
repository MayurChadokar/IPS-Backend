"""
Database initialization and table creation
Run this to create all tables
"""
from app.core.database import engine, Base
from app.models.models import College, Page, Section, SectionContent, PageTemplate


def init_db():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


if __name__ == "__main__":
    init_db()
