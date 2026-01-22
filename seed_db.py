"""
Seed database with sample data
"""
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import College, Page, Section, SectionContent


def seed_data():
    """Seed the database with sample data for IPSA"""
    db: Session = SessionLocal()
    
    try:
        # Check if data already exists
        existing = db.query(College).filter(College.slug == "ipsa").first()
        if existing:
            print("⚠️  Data already exists. Skipping seed.")
            return
        
        # Create IPSA College
        ipsa = College(
            name="IPSA - IPS Academy",
            slug="ipsa",
            logo="/uploads/ipsa-logo.png",
            domain="ipsa.edu",
            is_active=True
        )
        db.add(ipsa)
        db.flush()
        
        # Create Home Page
        home_page = Page(
            college_id=ipsa.id,
            slug="home",
            title="Home - IPSA",
            meta_description="Welcome to IPS Academy",
            is_active=True
        )
        db.add(home_page)
        db.flush()
        
        # Create Hero Section
        hero_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="hero",
            section_type="hero",
            sort_order=1,
            is_active=True
        )
        db.add(hero_section)
        db.flush()
        
        hero_content = SectionContent(
            section_id=hero_section.id,
            content_json={
                "images": ["/uploads/ipsa/hero-1.jpg", "/uploads/ipsa/hero-2.jpg"],
                "description": "Welcome to IPS Academy - Shaping Future Leaders",
                "cta_text": "Apply Now",
                "cta_link": "/apply"
            }
        )
        db.add(hero_content)
        
        # Create Why IPSA Section
        why_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="why_ipsa",
            section_type="text",
            sort_order=2,
            is_active=True
        )
        db.add(why_section)
        db.flush()
        
        why_content = SectionContent(
            section_id=why_section.id,
            content_json={
                "title": "Why Choose IPSA?",
                "subtitle": "Excellence in Education",
                "description": "IPSA offers world-class education with state-of-the-art facilities and experienced faculty.",
                "points": [
                    "Industry-oriented curriculum",
                    "Experienced faculty",
                    "Modern infrastructure",
                    "100% placement assistance"
                ]
            }
        )
        db.add(why_content)
        
        # Create Stats Section
        stats_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="stats",
            section_type="stats",
            sort_order=3,
            is_active=True
        )
        db.add(stats_section)
        db.flush()
        
        stats_content = SectionContent(
            section_id=stats_section.id,
            content_json={
                "stats": [
                    {"label": "Students", "value": "5000+"},
                    {"label": "Faculty", "value": "200+"},
                    {"label": "Courses", "value": "50+"},
                    {"label": "Placements", "value": "95%"}
                ]
            }
        )
        db.add(stats_content)
        
        # Create Accordion/FAQ Section
        accordion_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="faq",
            section_type="accordion",
            sort_order=4,
            is_active=True
        )
        db.add(accordion_section)
        db.flush()
        
        accordion_content = SectionContent(
            section_id=accordion_section.id,
            content_json={
                "title": "Frequently Asked Questions",
                "items": [
                    {
                        "question": "What courses does IPSA offer?",
                        "answer": "IPSA offers B.Tech, MBA, MCA, and various diploma programs."
                    },
                    {
                        "question": "What is the admission process?",
                        "answer": "Admissions are based on entrance exams and merit."
                    },
                    {
                        "question": "Does IPSA provide hostel facilities?",
                        "answer": "Yes, separate hostels for boys and girls with modern amenities."
                    }
                ]
            }
        )
        db.add(accordion_content)
        
        # Create About Page
        about_page = Page(
            college_id=ipsa.id,
            slug="about-us",
            title="About Us - IPSA",
            meta_description="Learn more about IPS Academy",
            is_active=True
        )
        db.add(about_page)
        db.flush()
        
        about_section = Section(
            college_id=ipsa.id,
            page_id=about_page.id,
            section_key="about_content",
            section_type="text",
            sort_order=1,
            is_active=True
        )
        db.add(about_section)
        db.flush()
        
        about_content = SectionContent(
            section_id=about_section.id,
            content_json={
                "title": "About IPS Academy",
                "content": "Established in 1999, IPS Academy has been at the forefront of quality education...",
                "vision": "To be a globally recognized institution",
                "mission": "Providing quality education and fostering innovation"
            }
        )
        db.add(about_content)
        
        # Create second college for demo
        college_a = College(
            name="College A",
            slug="college-a",
            logo="/uploads/college-a-logo.png",
            is_active=True
        )
        db.add(college_a)
        db.flush()
        
        # Home page for College A
        college_a_home = Page(
            college_id=college_a.id,
            slug="home",
            title="Home - College A",
            is_active=True
        )
        db.add(college_a_home)
        db.flush()
        
        college_a_hero = Section(
            college_id=college_a.id,
            page_id=college_a_home.id,
            section_key="hero",
            section_type="hero",
            sort_order=1,
            is_active=True
        )
        db.add(college_a_hero)
        db.flush()
        
        college_a_hero_content = SectionContent(
            section_id=college_a_hero.id,
            content_json={
                "images": ["/uploads/college-a/hero.jpg"],
                "description": "Welcome to College A - Building Tomorrow's Leaders",
                "cta_text": "Explore Programs",
                "cta_link": "/programs"
            }
        )
        db.add(college_a_hero_content)
        
        db.commit()
        print("✅ Database seeded successfully!")
        print("\n📊 Created:")
        print("   - 2 Colleges (IPSA, College A)")
        print("   - 3 Pages")
        print("   - 6 Sections with content")
        print("\n🔗 Try these endpoints:")
        print("   - GET /api/ipsa/pages/home")
        print("   - GET /api/college-a/pages/home")
        print("   - GET /api/colleges")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
