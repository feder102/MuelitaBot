"""Initial database schema.

Revision ID: 001
Create Date: 2026-04-04 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""
    # Create enum types
    conversation_state_enum = postgresql.ENUM(
        'AWAITING_MENU',
        'AWAITING_SELECTION',
        'APPOINTMENT_SELECTED',
        'SECRETARY_SELECTED',
        'COMPLETED',
        'INACTIVE',
        name='conversation_state_enum',
        create_type=True,
    )
    conversation_state_enum.create(op.get_bind())

    audit_status_enum = postgresql.ENUM(
        'SUCCESS',
        'VALIDATION_FAILED',
        'ERROR',
        name='audit_status_enum',
        create_type=True,
    )
    audit_status_enum.create(op.get_bind())

    # Create telegram_users table
    op.create_table(
        'telegram_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.func.gen_random_uuid()),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_user_id'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('ix_telegram_users_telegram_user_id', 'telegram_users', ['telegram_user_id'])
    op.create_index('ix_telegram_users_active', 'telegram_users', ['is_active', 'updated_at'], postgresql_using='btree')

    # Create conversation_state table
    op.create_table(
        'conversation_state',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_state', conversation_state_enum, nullable=False, server_default='AWAITING_MENU'),
        sa.Column('last_interaction', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('menu_display_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['telegram_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_index('ix_conversation_state_activity', 'conversation_state', ['current_state', 'last_interaction'])

    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.func.gen_random_uuid()),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('status', audit_status_enum, nullable=False),
        sa.Column('message_text', sa.Text(), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('request_headers', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['telegram_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action', 'status', 'created_at'])
    op.create_index('ix_audit_log_errors', 'audit_log', ['status'], postgresql_where=sa.text("status != 'SUCCESS'"))
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])


def downgrade() -> None:
    """Drop schema."""
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_errors', table_name='audit_log')
    op.drop_index('ix_audit_log_action', table_name='audit_log')
    op.drop_index('ix_audit_log_user_id', table_name='audit_log')
    op.drop_table('audit_log')

    op.drop_index('ix_conversation_state_activity', table_name='conversation_state')
    op.drop_table('conversation_state')

    op.drop_index('ix_telegram_users_active', table_name='telegram_users')
    op.drop_index('ix_telegram_users_telegram_user_id', table_name='telegram_users')
    op.drop_table('telegram_users')

    # Drop enums
    sa.Enum(name='audit_status_enum').drop(op.get_bind())
    sa.Enum(name='conversation_state_enum').drop(op.get_bind())
