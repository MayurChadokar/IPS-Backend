"""
Create a default admin user for initial login
"""
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User, UserRole


def create_admin():
    """Create default admin user"""
    db: Session = SessionLocal()
    
    try:
        # Check if admin already exists
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("⚠️  Admin user already exists.")
            print(f"   Username: {existing.username}")
            print(f"   Email: {existing.email}")
            return
        
        # Create admin user
        admin = User(
            email="admin@ipsa.edu",
            username="admin",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),  # Change this password!
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Admin user created successfully!")
        print("\n📝 Login Credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print("\n⚠️  IMPORTANT: Change this password after first login!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
