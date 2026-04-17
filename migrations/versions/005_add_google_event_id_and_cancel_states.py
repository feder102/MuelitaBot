"""Add google_event_id to appointments and cancel conversation states.

Revision ID: 005
Revises: 004
Create Date: 2026-04-12 00:00:00.000000

Feature 004 (Cancel Appointment):
- Adds google_event_id column to appointments table so calendar events can be
  deleted when an appointment is cancelled.
- Adds SELECTING_CANCELLATION_APPOINTMENT and AWAITING_CANCELLATION_CONFIRMATION
  values to the conversation_state_enum for the cancel flow state machine.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add google_event_id column to appointments table
    op.add_column(
        'appointments',
        sa.Column('google_event_id', sa.String(255), nullable=True)
    )
    op.create_index(
        'ix_appointments_google_event_id',
        'appointments',
        ['google_event_id'],
        unique=False,
    )

    # Add new conversation states for the cancel appointment flow
    op.execute(
        "ALTER TYPE conversationstateenum "
        "ADD VALUE IF NOT EXISTS 'SELECTING_CANCELLATION_APPOINTMENT'"
    )
    op.execute(
        "ALTER TYPE conversationstateenum "
        "ADD VALUE IF NOT EXISTS 'AWAITING_CANCELLATION_CONFIRMATION'"
    )


def downgrade() -> None:
    # Remove google_event_id column
    op.drop_index('ix_appointments_google_event_id', table_name='appointments')
    op.drop_column('appointments', 'google_event_id')

    # Note: PostgreSQL does not support removing enum values directly.
    # The SELECTING_CANCELLATION_APPOINTMENT and AWAITING_CANCELLATION_CONFIRMATION
    # values are left in the enum type. They will not be used after downgrade.
