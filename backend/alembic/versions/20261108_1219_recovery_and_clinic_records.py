"""recovery and clinic records

Revision ID: 0001
Revises:
Create Date: 2026-11-08 12:19:26.960265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.core.database


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = "0000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('care_invites',
    sa.Column('digest', sa.String(), nullable=False),
    sa.Column('clinic', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('expires', sa.DateTime(timezone=True), nullable=False),
    sa.Column('consumed', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('digest')
    )
    op.create_table('care_staff',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('clinic', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['clinicians.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('care_links',
    sa.Column('patient', app.core.database.GUID(), nullable=False),
    sa.Column('clinic', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['patient'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('patient')
    )
    op.create_index(op.f('ix_care_links_clinic'), 'care_links', ['clinic'], unique=False)
    op.create_table('care_records',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('patient', app.core.database.GUID(), nullable=False),
    sa.Column('clinic', sa.String(), nullable=True),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actor', sa.String(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['patient'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_care_records_patient'), 'care_records', ['patient'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_care_records_patient'), table_name='care_records')
    op.drop_table('care_records')
    op.drop_index(op.f('ix_care_links_clinic'), table_name='care_links')
    op.drop_table('care_links')
    op.drop_table('care_staff')
    op.drop_table('care_invites')
