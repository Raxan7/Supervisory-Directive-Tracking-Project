"""Drop finding_id from attachments — findings no longer own attachments."""
from alembic import op
import sqlalchemy as sa

revision = "0003_drop_finding_fk"
down_revision = "0002_examination_bank_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_attachments_finding_id", table_name="attachments")
    op.drop_foreign_key("fk_attachments_finding_id_findings", table_name="attachments")
    op.drop_column("attachments", "finding_id")


def downgrade() -> None:
    op.add_column("attachments", sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.finding_id", ondelete="CASCADE"), nullable=True, index=True))
