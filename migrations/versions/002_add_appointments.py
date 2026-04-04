"""Add appointments table for appointment booking feature.

Revision ID: 002
Revises: 001
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create appointments table and supporting types."""

    # Create enum type for appointment status
    appointment_status = postgresql.ENUM(
        'PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED',
        name='appointmentstatus'
    )
    appointment_status.create(op.get_bind(), checkfirst=True)

    # Create appointments table
    op.create_table(
        'appointments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('patient_user_id', sa.BigInteger, nullable=False),
        sa.Column('appointment_date', sa.Date, nullable=False),
        sa.Column('start_time', sa.Time, nullable=False),
        sa.Column('end_time', sa.Time, nullable=False),
        sa.Column('reason', sa.String(150), nullable=False),
        sa.Column('created_by_user_id', sa.BigInteger, nullable=True),
        sa.Column('created_by_phone', sa.String(20), nullable=True),
        sa.Column('status', appointment_status, nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('confirmed_at', sa.DateTime, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_appointments'),
        sa.ForeignKeyConstraint(
            ['patient_user_id'],
            ['telegram_users.id'],
            name='fk_appointments_patient_user_id',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['telegram_users.id'],
            name='fk_appointments_created_by_user_id',
            ondelete='SET NULL'
        ),
        sa.UniqueConstraint('appointment_date', 'start_time', name='uq_appointment_slot'),
        sa.CheckConstraint("char_length(reason) <= 150", name='ck_reason_length'),
        sa.CheckConstraint("end_time = start_time + INTERVAL '1 hour'", name='ck_appointment_duration'),
    )

    # Create indexes for performance
    op.create_index('idx_appointments_patient_user_id', 'appointments', ['patient_user_id'])
    op.create_index('idx_appointments_appointment_date', 'appointments', ['appointment_date'])
    op.create_index('idx_appointments_status', 'appointments', ['status'])
    op.create_index('idx_appointments_created_by_user_id', 'appointments', ['created_by_user_id'])


def downgrade() -> None:
    """Drop appointments table and enum type."""

    # Drop indexes
    op.drop_index('idx_appointments_created_by_user_id', table_name='appointments')
    op.drop_index('idx_appointments_status', table_name='appointments')
    op.drop_index('idx_appointments_appointment_date', table_name='appointments')
    op.drop_index('idx_appointments_patient_user_id', table_name='appointments')

    # Drop table
    op.drop_table('appointments')

    # Drop enum type
    appointment_status = postgresql.ENUM(
        'PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED',
        name='appointmentstatus'
    )
    appointment_status.drop(op.get_bind(), checkfirst=True)
