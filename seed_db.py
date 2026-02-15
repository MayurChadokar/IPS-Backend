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
            logo="https://picsum.photos/200/200",
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
                "images": ["https://picsum.photos/1200/600", "https://picsum.photos/1200/601"],
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
        
        # Create Features Section (Campus to Business)
        features_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="campus_features",
            section_type="features",
            sort_order=4,
            is_active=True
        )
        db.add(features_section)
        db.flush()
        
        features_content = SectionContent(
            section_id=features_section.id,
            content_json={
                "title": "Campus To Business Boardrooms",
                "subtitle": "Make it happen at IBMR",
                "items": [
                    "Legacy of 30 years",
                    "58-acre Lush Green Campus",
                    "500+ Faculty Members",
                    "500+ Eminent Recruiters",
                    "100000+ Alumni Network",
                    "Ranked among Top 50 Management Institutes",
                    "NAAC A++ Accredited & NIRF Ranked (76-100 band)",
                    "Approved Management & Economics Ph.D Research Centre of DAVV",
                    "10,000+ Changemakers Community",
                    "Harvard Case Studies & Real-time Simulations Based Learning"
                ]
            }
        )
        db.add(features_content)
        
        # Create Advantage Section (Experience, Learn, Lead)
        advantage_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="advantage",
            section_type="cards",
            sort_order=5,
            is_active=True
        )
        db.add(advantage_section)
        db.flush()
        
        advantage_content = SectionContent(
            section_id=advantage_section.id,
            content_json={
                "title": "Experience, Learn, Lead: The IBMR Advantage",
                "cards": [
                    {
                        "title": "Experiential Learning",
                        "description": "Industry projects, internships, and case studies",
                        "icon": "https://res.cloudinary.com/demo/image/upload/v1624450355/sample.jpg"
                    },
                    {
                        "title": "Skill Development",
                        "description": "Value-added certifications in analytics, digital marketing, NSF and more",
                        "icon": "https://res.cloudinary.com/demo/image/upload/v1624450355/sample.jpg"
                    },
                    {
                        "title": "Research Focus",
                        "description": "Opportunities for publication in national and international journals",
                        "icon": "https://res.cloudinary.com/demo/image/upload/v1624450355/sample.jpg"
                    },
                    {
                        "title": "Holistic Growth",
                        "description": "Personality development, leadership workshops, and cultural events",
                        "icon": "https://res.cloudinary.com/demo/image/upload/v1624450355/sample.jpg"
                    },
                    {
                        "title": "Internship & Projects",
                        "description": "Industrial projects in various domains for real-world exposure",
                        "icon": "https://res.cloudinary.com/demo/image/upload/v1624450355/sample.jpg"
                    },
                    {
                        "title": "Industry Connect",
                        "description": "Guest lectures, industrial visits, and networking events with top leaders",
                        "icon": "https://res.cloudinary.com/demo/image/upload/v1624450355/sample.jpg"
                    }
                ]
            }
        )
        db.add(advantage_content)
        
        # Create Accordion/FAQ Section
        accordion_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="faq",
            section_type="accordion",
            sort_order=6,
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
        
        # Create Programs Section
        programs_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="programs_table",
            section_type="programs",
            sort_order=7,
            is_active=True
        )
        db.add(programs_section)
        db.flush()
        
        programs_content = SectionContent(
            section_id=programs_section.id,
            content_json={
                "title": "Programmes Offered",
                "programs": [
                    {
                        "name": "MBA (Core)",
                        "details": "Build a strong foundation in business leadership... Program Highlights: Interactive problem-solving classes...",
                        "eligibility": "Graduation in any discipline with minimum 50% marks..."
                    }
                ]
            }
        )
        db.add(programs_content)
        
        # Create Facilities Section
        facilities_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="campus_facilities",
            section_type="facilities",
            sort_order=8,
            is_active=True
        )
        db.add(facilities_section)
        db.flush()
        
        facilities_content = SectionContent(
            section_id=facilities_section.id,
            content_json={
                "title": "Facilities",
                "subtitle": "60 acres of excellence. Limitless success for you.",
                "description": "IBMR is more than a campus. It is a thriving community to explore, learn and grow with like-minded peers.",
                "facilities": [
                    {
                        "name": "LIBRARY",
                        "description": "State-of-the-art library housing over 35,000 books...",
                        "image": "https://picsum.photos/800/600?random=1"
                    },
                    {
                        "name": "CLASSROOMS",
                        "description": "Spacious, bright and well-ventilated classrooms...",
                        "image": "https://picsum.photos/800/600?random=2"
                    },
                    {
                        "name": "COMPUTER LABS",
                        "description": "Advanced systems and seamless Wi-Fi connectivity...",
                        "image": "https://picsum.photos/800/600?random=3"
                    },
                    {
                        "name": "SEMINAR HALL",
                        "description": "Equipped with modern audio-visual facilities...",
                        "image": "https://picsum.photos/800/600?random=4"
                    }
                ]
            }
        )
        db.add(facilities_content)
        
        # Create Placement Section (Split)
        placement_section = Section(
            college_id=ipsa.id,
            page_id=home_page.id,
            section_key="placements",
            section_type="split",
            sort_order=9,
            is_active=True
        )
        db.add(placement_section)
        db.flush()
        
        placement_content = SectionContent(
            section_id=placement_section.id,
            content_json={
                "tag": "PLACEMENT",
                "title": "So Will You They Made It Happen At IBMR",
                "description": "At IBMR, classroom learning meets real-world success. Our dedicated placement support transitions students from academics to industry through training, internships, mentorship, and global recruiter opportunities.",
                "items": [
                    "Tailored career guidance and mentorship",
                    "Soft skills & interview training",
                    "Top recruiters & lucrative packages"
                ],
                "image": "https://picsum.photos/1000/800?random=5",
                "image_position": "right"
            }
        )
        db.add(placement_content)
        
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
            logo="https://picsum.photos/201/201",
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
                "images": ["https://picsum.photos/1200/602"],
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
