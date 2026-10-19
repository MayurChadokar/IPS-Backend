"""Add college career openings and seed the IPSA career CMS page.

Revision ID: 6f2e9d1c8a40
Revises: 5213a7692f59
"""
from alembic import context, op
import sqlalchemy as sa


revision = "6f2e9d1c8a40"
down_revision = "5213a7692f59"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "career_openings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("short_description", sa.String(1000), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("qualifications", sa.Text(), nullable=True),
        sa.Column("apply_url", sa.String(1000), nullable=False),
        sa.Column("closing_date", sa.Date(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("ix_career_openings_id", "career_openings", ["id"])
    op.create_index("ix_career_openings_college_active", "career_openings", ["college_id", "is_active"])
    if not context.is_offline_mode():
        seed_ipsa_page(op.get_bind())


def seed_ipsa_page(connection):
    """Add missing content only; preserve any existing career page and sections."""
    metadata = sa.MetaData()
    colleges = sa.Table("colleges", metadata, autoload_with=connection)
    pages = sa.Table("pages", metadata, autoload_with=connection)
    sections = sa.Table("sections", metadata, autoload_with=connection)
    contents = sa.Table("section_contents", metadata, autoload_with=connection)
    college_id = connection.execute(sa.select(colleges.c.id).where(colleges.c.slug == "ipsa")).scalar()
    if college_id is None:
        return
    page_id = connection.execute(sa.select(pages.c.id).where(pages.c.college_id == college_id, pages.c.slug == "career")).scalar()
    if page_id is None:
        result = connection.execute(pages.insert().values(
            college_id=college_id, slug="career", title="Careers - IPS Academy", meta_title="Careers - IPS Academy",
            meta_description="Build your career at IPS Academy. Explore current faculty, administration and support openings.",
            robots="index, follow", is_active=True,
        ))
        page_id = result.inserted_primary_key[0]
    defaults = [
        ("hero", "hero", {"images": [], "alt": "Build your career at IPS Academy"}),
        ("career_introduction", "text", {
            "title": "Build Your Career at IPS Academy",
            "description": "IPS Academy brings together a legacy of academic excellence, diverse disciplines and a strong commitment to shaping future-ready professionals. With a vibrant academic ecosystem and a focus on innovation, research and industry relevance, we create an environment where ideas take shape and expertise creates impact.",
        }),
        ("current_openings", "custom", {
            "title": "Current Openings", "categories": ["Faculty Positions", "Administration", "Support Staff"],
            "job_types": ["Full Time", "Part Time", "Contract", "Visiting Faculty"],
            "api_endpoint": "/api/ipsa/careers", "filters_endpoint": "/api/ipsa/careers/filters", "apply_button_text": "Apply Now",
        }),
    ]
    for order, (key, kind, content) in enumerate(defaults, 1):
        section_id = connection.execute(sa.select(sections.c.id).where(sections.c.page_id == page_id, sections.c.section_key == key)).scalar()
        if section_id is None:
            result = connection.execute(sections.insert().values(college_id=college_id, page_id=page_id, section_key=key, section_type=kind, sort_order=order, is_active=True))
            section_id = result.inserted_primary_key[0]
        if connection.execute(sa.select(contents.c.id).where(contents.c.section_id == section_id)).scalar() is None:
            connection.execute(contents.insert().values(section_id=section_id, content_json=content))


def downgrade():
    # Keep authored CMS content when rolling back the openings feature.
    op.drop_index("ix_career_openings_college_active", table_name="career_openings")
    op.drop_index("ix_career_openings_id", table_name="career_openings")
    op.drop_table("career_openings")
