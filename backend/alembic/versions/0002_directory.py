"""Add station administration and register historical clinic names."""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4
from app.core.database import GUID

revision = "0002"
down_revision = "0001"
branch_labels = depends_on = None


def upgrade():
    op.create_table("care_administrators", sa.Column("id", GUID(), primary_key=True),
                    sa.Column("email", sa.String(200), nullable=False, unique=True),
                    sa.Column("hashed_password", sa.String(200), nullable=False))
    clinics = op.create_table("care_clinics", sa.Column("id", GUID(), primary_key=True),
                              sa.Column("scope", sa.String(), nullable=False, unique=True),
                              sa.Column("name", sa.String(), nullable=False),
                              sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_index("uq_active_clinic_name", "care_clinics", ["name"], unique=True,
                    sqlite_where=sa.text("deleted_at IS NULL"), postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_table("care_closed_profiles",
                    sa.Column("patient", GUID(), sa.ForeignKey("patients.id"), primary_key=True),
                    sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("care_directory_audit", sa.Column("id", GUID(), primary_key=True),
                    sa.Column("at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("actor", GUID(), nullable=False), sa.Column("action", sa.String(50), nullable=False),
                    sa.Column("target", GUID()))
    db = op.get_bind()
    names = db.execute(sa.text("SELECT clinic FROM care_staff UNION SELECT clinic FROM care_links "
                               "UNION SELECT clinic FROM care_invites UNION SELECT clinic FROM care_records")).scalars().all()
    for name in names:
        if name is not None:
            db.execute(clinics.insert().values(id=uuid4(), name=name, scope=name))


def downgrade():
    for table in ("care_directory_audit", "care_closed_profiles", "care_clinics", "care_administrators"):
        op.drop_table(table)
