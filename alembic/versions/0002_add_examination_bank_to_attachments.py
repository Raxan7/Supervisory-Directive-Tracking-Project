"""Add examination_id and bank_id to attachments, make finding_id nullable."""
from alembic import op
import sqlalchemy as sa

revision = "0002_examination_bank_fk"
down_revision = "0001_original_architecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attachments", sa.Column("examination_id", sa.Integer(), sa.ForeignKey("examinations.examination_id", ondelete="CASCADE"), nullable=True, index=True))
    op.add_column("attachments", sa.Column("bank_id", sa.Integer(), sa.ForeignKey("banks.bank_id", ondelete="CASCADE"), nullable=True, index=True))
    op.alter_column("attachments", "finding_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("attachments", "finding_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("attachments", "bank_id")
    op.drop_column("attachments", "examination_id")
