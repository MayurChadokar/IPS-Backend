# Example API Usage

## Test with sample data after running seed_db.py

### 1. Get IPSA Home Page
```bash
curl http://localhost:3000/api/ipsa/pages/home
```

### 2. Get College A Home Page
```bash
curl http://localhost:3000/api/college-a/pages/home
```

### 3. List All Colleges
```bash
curl http://localhost:3000/api/colleges
```

### 4. List IPSA Pages
```bash
curl http://localhost:3000/api/ipsa/pages
```

### 5. Create New College (Admin)
```bash
curl -X POST http://localhost:3000/api/admin/colleges \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test College",
    "slug": "test-college",
    "is_active": true
  }'
```

### 6. Create Page for College
```bash
curl -X POST http://localhost:3000/api/admin/pages \
  -H "Content-Type: application/json" \
  -d '{
    "college_id": 1,
    "slug": "contact",
    "title": "Contact Us",
    "is_active": true
  }'
```

### 7. Create Section with Content
```bash
curl -X POST http://localhost:3000/api/admin/sections \
  -H "Content-Type: application/json" \
  -d '{
    "college_id": 1,
    "page_id": 1,
    "section_key": "contact_form",
    "section_type": "form",
    "sort_order": 1,
    "content_json": {
      "title": "Get in Touch",
      "fields": ["name", "email", "message"],
      "submit_text": "Send Message"
    }
  }'
```

### 8. Update Section Content
```bash
curl -X PUT http://localhost:3000/api/admin/sections/1 \
  -H "Content-Type: application/json" \
  -d '{
    "content_json": {
      "images": ["https://res.cloudinary.com/.../new-hero.jpg"],
      "description": "Updated description"
    }
  }'
```

### 9. Upload File to Cloudinary (Admin)
```bash
curl -X POST http://localhost:3000/api/admin/upload \
  -F "file=@your_image.jpg" \
  -F "folder=college_logos"
```

### 10. Clone Page Between Colleges
```bash
curl -X POST http://localhost:3000/api/admin/pages/clone \
  -H "Content-Type: application/json" \
  -d '{
    "source_college_slug": "ipsa",
    "source_page_slug": "home",
    "target_college_slug": "test-college",
    "new_page_title": "Home - Test College"
  }'
```

### 11. List All Pages for a College
```bash
curl http://localhost:3000/api/admin/colleges/1/pages
```
