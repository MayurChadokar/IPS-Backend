# Multi-College CMS - FastAPI Backend

A scalable, multi-tenant CMS system for managing multiple college websites from a single backend.

## 🎯 Architecture Overview

```
System
 └── Colleges (IPSA, College A, College B...)
      └── Pages (Home, About, Contact...)
           └── Sections (Hero, Stats, Accordion...)
                └── Content (JSON)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your MySQL database credentials:
```env
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/multi_college_cms
```

### 3. Create Database

```sql
CREATE DATABASE multi_college_cms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Initialize Tables

```bash
python init_db.py
```

### 5. Seed Sample Data

```bash
python seed_db.py
```

### 6. Run the Server

```bash
uvicorn main:app --reload --port 3000
```

Server will start at: http://localhost:3000

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**: http://localhost:3000/redoc

## 🔑 Key API Endpoints

### Public API (For Frontend)

```bash
# Get page data for a college
GET /api/{college_slug}/pages/{page_slug}
Example: GET /api/ipsa/pages/home

Response:
{
  "college": "ipsa",
  "page": "home",
  "title": "Home - IPSA",
  "sections": {
    "hero": {
      "type": "hero",
      "sort_order": 1,
      "images": [...],
      "description": "...",
      "cta_text": "Apply Now"
    },
    "why_ipsa": {...},
    "stats": {...},
    "faq": {...}
  }
}

# List all pages for a college
GET /api/{college_slug}/pages
Example: GET /api/ipsa/pages

# List all active colleges
GET /api/colleges
```

### Admin API

#### Colleges
```bash
POST   /api/admin/colleges           # Create college
GET    /api/admin/colleges           # List colleges
GET    /api/admin/colleges/{id}      # Get college
PUT    /api/admin/colleges/{id}      # Update college
DELETE /api/admin/colleges/{id}      # Delete college
```

#### Pages
```bash
POST   /api/admin/pages                      # Create page
GET    /api/admin/colleges/{id}/pages        # List pages
GET    /api/admin/pages/{id}                 # Get page
PUT    /api/admin/pages/{id}                 # Update page
DELETE /api/admin/pages/{id}                 # Delete page
POST   /api/admin/pages/clone                # Clone page between colleges
```

#### Sections
```bash
POST   /api/admin/sections              # Create section
GET    /api/admin/pages/{id}/sections   # List sections
GET    /api/admin/sections/{id}         # Get section
PUT    /api/admin/sections/{id}         # Update section
DELETE /api/admin/sections/{id}         # Delete section
```

## 📊 Database Schema

### Tables

1. **colleges** - Main tenant table
   - id, name, slug, logo, domain, is_active

2. **pages** - College pages
   - id, college_id, slug, title, meta_description, is_active

3. **sections** - Page sections
   - id, college_id, page_id, section_key, section_type, sort_order, is_active

4. **section_contents** - JSON content
   - id, section_id, content_json

5. **page_templates** - Optional templates
   - id, template_key, name, template_json

## 🎨 Section Types

- **hero** - Hero/banner sections
- **text** - Text content sections
- **stats** - Statistics/numbers
- **accordion** - FAQ/Accordion
- **image** - Image galleries
- **custom** - Any custom type

## 🔧 Usage Examples

### Create a New College

```bash
POST /api/admin/colleges
{
  "name": "New College",
  "slug": "new-college",
  "logo": "/uploads/logo.png",
  "is_active": true
}
```

### Create a Page

```bash
POST /api/admin/pages
{
  "college_id": 1,
  "slug": "home",
  "title": "Home Page",
  "is_active": true
}
```

### Create a Section with Content

```bash
POST /api/admin/sections
{
  "college_id": 1,
  "page_id": 1,
  "section_key": "hero",
  "section_type": "hero",
  "sort_order": 1,
  "content_json": {
    "images": ["/uploads/hero.jpg"],
    "description": "Welcome!",
    "cta_text": "Get Started",
    "cta_link": "/apply"
  }
}
```

### Clone a Page Between Colleges

```bash
POST /api/admin/pages/clone
{
  "source_college_slug": "ipsa",
  "source_page_slug": "home",
  "target_college_slug": "new-college",
  "new_page_title": "Home - New College"
}
```

## 🌐 Angular Frontend Integration

### Option 1: Subdomain Detection (Recommended)

```typescript
// Detect college from subdomain
const hostname = window.location.hostname; // ipsa.example.com
const collegeSlug = hostname.split('.')[0]; // "ipsa"

// Fetch page data
this.http.get(`/api/${collegeSlug}/pages/home`)
  .subscribe(data => {
    this.heroSection = data.sections.hero;
    this.statsSection = data.sections.stats;
  });
```

### Option 2: URL Path

```typescript
// Route: /:college/home
this.collegeSlug = this.route.snapshot.params['college'];
this.http.get(`/api/${this.collegeSlug}/pages/home`)
  .subscribe(data => { /* ... */ });
```

### Option 3: Domain Mapping

Backend automatically resolves college by domain.

## 📁 Project Structure

```
IPS-backend/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── public.py      # Public frontend API
│   │   └── admin.py       # Admin CRUD API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py      # Settings
│   │   └── database.py    # DB connection
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py      # SQLAlchemy models
│   └── schemas/
│       ├── __init__.py
│       └── schemas.py     # Pydantic schemas
├── uploads/               # File uploads
├── main.py               # FastAPI app
├── init_db.py            # Create tables
├── seed_db.py            # Sample data
├── requirements.txt
├── .env.example
└── README.md
```

## ✅ Key Features

- ✅ Multi-tenant architecture (one system, multiple colleges)
- ✅ Fully dynamic content (no hardcoding)
- ✅ JSON-driven sections
- ✅ Easy to clone pages between colleges
- ✅ RESTful API design
- ✅ Automatic cascade deletion
- ✅ Scalable and maintainable
- ✅ SEO friendly (meta descriptions)
- ✅ CORS enabled for Angular

## 🎯 Best Practices

1. **Same frontend code for all colleges** - Detect college and fetch data
2. **JSON content** - Flexible and easy to modify
3. **Section ordering** - Use `sort_order` for arrangement
4. **Active flags** - Enable/disable without deletion
5. **Clone feature** - Reuse pages across colleges

## 🔐 Future Enhancements

- [ ] Authentication & Authorization
- [ ] File upload endpoints
- [ ] Image optimization
- [ ] Caching layer (Redis)
- [ ] Search functionality
- [ ] Analytics integration
- [ ] Multi-language support
- [ ] Revision history

## 📞 Support

For issues and questions, refer to the API documentation at `/docs`.

---

**Built with FastAPI** 🚀
