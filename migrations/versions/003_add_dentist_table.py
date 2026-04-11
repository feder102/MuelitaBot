"""Add dentist table for multi-dentist appointment booking.

Revision ID: 003
Revises: 002
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create dentist table and update appointments table."""

    # Create dentist table
    op.create_table(
        'dentists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('calendar_id', sa.String(255), nullable=False),
        sa.Column('active_status', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id', name='pk_dentists'),
        sa.UniqueConstraint('name', name='uq_dentist_name'),
        sa.UniqueConstraint('calendar_id', name='uq_dentist_calendar_id'),
    )

    # Create indexes on dentists
    op.create_index('idx_dentist_active_status', 'dentists', ['active_status'])
    op.create_index('idx_dentist_name', 'dentists', ['name'])

    # Add dentist_id column to appointments
    op.add_column('appointments', sa.Column('dentist_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('idx_appointment_dentist_id', 'appointments', ['dentist_id'])

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_appointments_dentist_id',
        'appointments', 'dentists',
        ['dentist_id'], ['id'],
        ondelete='RESTRICT'
    )

    # Drop old unique constraint and create new one with dentist_id
    op.drop_constraint('uq_appointment_slot', 'appointments', type_='unique')
    op.create_unique_constraint(
        'uq_appointment_slot_per_dentist',
        'appointments',
        ['dentist_id', 'appointment_date', 'start_time']
    )


def downgrade() -> None:
    """Revert dentist table and appointments changes."""

    # Drop unique constraint
    op.drop_constraint('uq_appointment_slot_per_dentist', 'appointments', type_='unique')
    op.create_unique_constraint(
        'uq_appointment_slot',
        'appointments',
        ['appointment_date', 'start_time']
    )

    # Remove foreign key and column
    op.drop_constraint('fk_appointments_dentist_id', 'appointments', type_='foreignkey')
    op.drop_index('idx_appointment_dentist_id', 'appointments')
    op.drop_column('appointments', 'dentist_id')

    # Drop dentist table
    op.drop_index('idx_dentist_name', 'dentists')
    op.drop_index('idx_dentist_active_status', 'dentists')
    op.drop_table('dentists')
