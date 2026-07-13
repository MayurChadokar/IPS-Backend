"""
Change password for an existing admin user.
Run this script on the live server to securely update the password.
Usage: python change_admin_password.py <username> <new_password>
"""
import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User

def change_password(username: str, new_password: str):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ User '{username}' not found in database.")
            return

        user.hashed_password = get_password_hash(new_password)
        db.commit()
        print(f"✅ Password for '{username}' has been successfully updated!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating password: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python change_admin_password.py <username> <new_password>")
        print("Example: python change_admin_password.py admin MySuperSecret123!")
        sys.exit(1)
        
    admin_user = sys.argv[1]
    new_pass = sys.argv[2]
    
    # Confirm prompt to avoid accidental changes
    confirm = input(f"Are you sure you want to change the password for '{admin_user}'? (y/n): ")
    if confirm.lower() == 'y':
        change_password(admin_user, new_pass)
    else:
        print("Aborted.")
