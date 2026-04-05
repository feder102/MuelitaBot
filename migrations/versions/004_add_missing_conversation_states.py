"""Add missing conversation states for appointment booking features.

Revision ID: 004
Create Date: 2026-04-05 22:00:00.000000

Feature 002 (Appointment Booking) and Feature 003 (Multi-Dentist) added new states
that were missing from the initial enum definition.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing SELECTING_DENTIST state to conversation_state enum.

    Note: The enum is named 'conversationstateenum' (lowercase) in the database.
    """
    # Add SELECTING_DENTIST state for Feature 003 (Multi-Dentist Booking)
    op.execute("ALTER TYPE conversationstateenum ADD VALUE 'SELECTING_DENTIST'")


def downgrade() -> None:
    """Remove added conversation states.

    Note: In PostgreSQL, we cannot directly remove enum values.
    To downgrade, you would need to:
    1. Create a new enum type without the values
    2. Convert the column to use the new type
    3. Drop the old type

    This is complex and not recommended for production. Instead,
    keep the enum values but don't use them.
    """
    pass
