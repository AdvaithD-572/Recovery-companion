"""Original patient diary schema

Revision ID: 0000
Revises:
Create Date: 2026-11-08 12:19:26.960265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.core.database


# revision identifiers, used by Alembic.
revision: str = '0000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('clinicians',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('hashed_password', sa.String(length=200), nullable=False),
    sa.Column('specialty', sa.String(length=100), nullable=True),
    sa.Column('hospital', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('patients',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('hashed_password', sa.String(length=200), nullable=False),
    sa.Column('dob', sa.Date(), nullable=True),
    sa.Column('gender', sa.String(length=20), nullable=True),
    sa.Column('height_cm', sa.SmallInteger(), nullable=True),
    sa.Column('weight_kg', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('primary_condition', sa.String(length=200), nullable=True),
    sa.Column('surgery_type', sa.String(length=200), nullable=True),
    sa.Column('discharge_date', sa.Date(), nullable=True),
    sa.Column('chronic_diseases', sa.JSON(), nullable=True),
    sa.Column('allergies', sa.JSON(), nullable=True),
    sa.Column('eating_habits', sa.String(length=100), nullable=True),
    sa.Column('exercise_frequency', sa.String(length=50), nullable=True),
    sa.Column('smoking', sa.Boolean(), nullable=False),
    sa.Column('alcohol', sa.Boolean(), nullable=False),
    sa.Column('sleep_baseline', sa.Numeric(precision=3, scale=1), nullable=True),
    sa.Column('mood_baseline', sa.Numeric(precision=3, scale=1), nullable=True),
    sa.Column('living_situation', sa.String(length=50), nullable=True),
    sa.Column('emergency_contact', sa.JSON(), nullable=True),
    sa.Column('preferred_language', sa.String(length=10), nullable=False),
    sa.Column('fcm_token', sa.Text(), nullable=True),
    sa.Column('onboarding_complete', sa.Boolean(), nullable=False),
    sa.Column('clinician_id', app.core.database.GUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['clinician_id'], ['clinicians.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('consent_ledger',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('patient_id', app.core.database.GUID(), nullable=False),
    sa.Column('consent_type', sa.String(length=80), nullable=False),
    sa.Column('granted', sa.Boolean(), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('version', sa.String(length=10), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('daily_logs',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('patient_id', app.core.database.GUID(), nullable=False),
    sa.Column('log_date', sa.Date(), nullable=False),
    sa.Column('pain_score', sa.SmallInteger(), nullable=True),
    sa.Column('sleep_score', sa.SmallInteger(), nullable=True),
    sa.Column('appetite_score', sa.SmallInteger(), nullable=True),
    sa.Column('mood_score', sa.SmallInteger(), nullable=True),
    sa.Column('fatigue_score', sa.SmallInteger(), nullable=True),
    sa.Column('mobility_score', sa.SmallInteger(), nullable=True),
    sa.Column('swelling_score', sa.SmallInteger(), nullable=True),
    sa.Column('medicine_adherence', sa.SmallInteger(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('submission_method', sa.String(length=20), nullable=False),
    sa.Column('insight', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_daily_logs_log_date'), 'daily_logs', ['log_date'], unique=False)
    op.create_table('digital_twins',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('patient_id', app.core.database.GUID(), nullable=False),
    sa.Column('expected_pain_curve', sa.JSON(), nullable=True),
    sa.Column('expected_fatigue_curve', sa.JSON(), nullable=True),
    sa.Column('expected_appetite_curve', sa.JSON(), nullable=True),
    sa.Column('expected_mood_curve', sa.JSON(), nullable=True),
    sa.Column('expected_mobility_curve', sa.JSON(), nullable=True),
    sa.Column('expected_sleep_curve', sa.JSON(), nullable=True),
    sa.Column('baseline_bmi', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('baseline_age_group', sa.String(length=20), nullable=True),
    sa.Column('baseline_condition', sa.String(length=100), nullable=True),
    sa.Column('model_version', sa.String(length=20), nullable=False),
    sa.Column('calibrated', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('patient_id')
    )
    op.create_table('escalation_flags',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('patient_id', app.core.database.GUID(), nullable=False),
    sa.Column('flag_date', sa.Date(), nullable=False),
    sa.Column('metric', sa.String(length=20), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('expected_value', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('actual_value', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('deviation_pct', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('patient_insight', sa.Text(), nullable=True),
    sa.Column('clinician_summary', sa.Text(), nullable=True),
    sa.Column('clarified_by_user', sa.Boolean(), nullable=False),
    sa.Column('user_clarification', sa.Text(), nullable=True),
    sa.Column('clinician_reviewed', sa.Boolean(), nullable=False),
    sa.Column('suppressed', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_escalation_flags_flag_date'), 'escalation_flags', ['flag_date'], unique=False)
    op.create_table('food_logs',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('patient_id', app.core.database.GUID(), nullable=False),
    sa.Column('meal_type', sa.String(length=20), nullable=False),
    sa.Column('food_items', sa.JSON(), nullable=False),
    sa.Column('image_s3_key', sa.String(length=500), nullable=True),
    sa.Column('cv_confidence', sa.Numeric(precision=3, scale=2), nullable=True),
    sa.Column('interaction_flags', sa.JSON(), nullable=False),
    sa.Column('caution_shown', sa.Boolean(), nullable=False),
    sa.Column('logged_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('prescriptions',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('patient_id', app.core.database.GUID(), nullable=False),
    sa.Column('drug_name', sa.String(length=200), nullable=False),
    sa.Column('generic_name', sa.String(length=200), nullable=True),
    sa.Column('dosage', sa.String(length=50), nullable=False),
    sa.Column('frequency', sa.JSON(), nullable=False),
    sa.Column('is_compulsory', sa.Boolean(), nullable=False),
    sa.Column('total_doses_bought', sa.Integer(), nullable=False),
    sa.Column('doses_remaining', sa.Integer(), nullable=False),
    sa.Column('refill_threshold', sa.Integer(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('dose_logs',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('prescription_id', app.core.database.GUID(), nullable=False),
    sa.Column('patient_id', app.core.database.GUID(), nullable=False),
    sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('taken_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('skipped', sa.Boolean(), nullable=False),
    sa.Column('skip_reason', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('reminders',
    sa.Column('id', app.core.database.GUID(), nullable=False),
    sa.Column('patient_id', app.core.database.GUID(), nullable=False),
    sa.Column('reminder_type', sa.String(length=30), nullable=False),
    sa.Column('scheduled_time', sa.String(length=5), nullable=False),
    sa.Column('days_of_week', sa.JSON(), nullable=False),
    sa.Column('prescription_id', app.core.database.GUID(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('quiet_hours_start', sa.String(length=5), nullable=True),
    sa.Column('quiet_hours_end', sa.String(length=5), nullable=True),
    sa.Column('last_sent', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('reminders')
    op.drop_table('dose_logs')
    op.drop_table('prescriptions')
    op.drop_table('food_logs')
    op.drop_index(op.f('ix_escalation_flags_flag_date'), table_name='escalation_flags')
    op.drop_table('escalation_flags')
    op.drop_table('digital_twins')
    op.drop_index(op.f('ix_daily_logs_log_date'), table_name='daily_logs')
    op.drop_table('daily_logs')
    op.drop_table('consent_ledger')
    op.drop_table('patients')
    op.drop_table('clinicians')
