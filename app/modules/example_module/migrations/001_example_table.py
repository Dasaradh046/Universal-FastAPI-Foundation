"""create example table

Revision ID: 001_example_table
Revises: 
Create Date: 2026-10-14 12:27:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_example_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema."""
    op.create_table(
        'examples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_examples_id'), 'examples', ['id'], unique=False)
    op.create_index(op.f('ix_examples_name'), 'examples', ['name'], unique=False)


def downgrade():
    """Downgrade database schema."""
    op.drop_index(op.f('ix_examples_name'), table_name='examples')
    op.drop_index(op.f('ix_examples_id'), table_name='examples')
    op.drop_table('examples')
