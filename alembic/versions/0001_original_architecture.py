"""Create the 12-table original database architecture."""
from alembic import op
import sqlalchemy as sa

revision = "0001_original_architecture"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role=sa.Enum("EXAMINER","MANAGER","ADMIN",name="user_role")
    status=sa.Enum("OPEN","IN_PROGRESS","CLOSED","OVERDUE",name="finding_status")
    severity=sa.Enum("LOW","MEDIUM","HIGH","CRITICAL",name="finding_severity")
    op.create_table("users",sa.Column("user_id",sa.Integer(),primary_key=True),sa.Column("full_name",sa.String(160),nullable=False),sa.Column("email",sa.String(255),nullable=False,unique=True),sa.Column("role",role,nullable=False),sa.Column("password_hash",sa.String(255),nullable=False),sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()))
    op.create_table("banks",sa.Column("bank_id",sa.Integer(),primary_key=True),sa.Column("bank_name",sa.String(180),nullable=False,unique=True),sa.Column("bank_code",sa.String(40),nullable=False,unique=True),sa.Column("bank_type",sa.String(100),nullable=False))
    op.create_table("risk_outcomes",sa.Column("risk_outcome_id",sa.Integer(),primary_key=True),sa.Column("bank_id",sa.Integer(),sa.ForeignKey("banks.bank_id",ondelete="CASCADE"),nullable=False),sa.Column("risk_category",sa.String(120),nullable=False),sa.Column("risk_rating",sa.String(80),nullable=False),sa.Column("assessment_date",sa.Date(),nullable=False))
    op.create_table("examinations",sa.Column("examination_id",sa.Integer(),primary_key=True),sa.Column("bank_id",sa.Integer(),sa.ForeignKey("banks.bank_id",ondelete="RESTRICT"),nullable=False),sa.Column("examination_type",sa.String(120),nullable=False),sa.Column("start_date",sa.Date(),nullable=False),sa.Column("end_date",sa.Date()),sa.Column("report_date",sa.Date()),sa.Column("examination_cycle",sa.String(80),nullable=False))
    op.create_table("findings",sa.Column("finding_id",sa.Integer(),primary_key=True),sa.Column("examination_id",sa.Integer(),sa.ForeignKey("examinations.examination_id",ondelete="CASCADE"),nullable=False),sa.Column("bank_id",sa.Integer(),sa.ForeignKey("banks.bank_id",ondelete="RESTRICT"),nullable=False),sa.Column("examiner_id",sa.Integer(),sa.ForeignKey("users.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("title",sa.String(240),nullable=False),sa.Column("description",sa.Text(),nullable=False),sa.Column("risk_category",sa.String(120),nullable=False),sa.Column("severity",severity,nullable=False),sa.Column("deadline",sa.Date(),nullable=False),sa.Column("status",status,nullable=False),sa.Column("date_closed",sa.Date()),sa.Column("repeat_flag",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("chronic_flag",sa.Boolean(),nullable=False,server_default=sa.false()))
    directive_status=sa.Enum("OPEN","IN_PROGRESS","CLOSED","OVERDUE",name="directive_status")
    op.create_table("directives",sa.Column("directive_id",sa.Integer(),primary_key=True),sa.Column("finding_id",sa.Integer(),sa.ForeignKey("findings.finding_id",ondelete="CASCADE"),nullable=False),sa.Column("directive_title",sa.Text(),nullable=False),sa.Column("deadline",sa.Date(),nullable=False),sa.Column("status",directive_status,nullable=False))
    action_status=sa.Enum("OPEN","IN_PROGRESS","CLOSED","OVERDUE",name="action_status")
    op.create_table("remedial_actions",sa.Column("action_id",sa.Integer(),primary_key=True),sa.Column("directive_id",sa.Integer(),sa.ForeignKey("directives.directive_id",ondelete="CASCADE"),nullable=False),sa.Column("action_description",sa.Text(),nullable=False),sa.Column("deadline",sa.Date(),nullable=False),sa.Column("status",action_status,nullable=False),sa.Column("completion_date",sa.Date()))
    op.create_table("audit_logs",sa.Column("audit_id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("action",sa.String(120),nullable=False),sa.Column("entity",sa.String(100),nullable=False),sa.Column("entity_id",sa.Integer(),nullable=False),sa.Column("timestamp",sa.DateTime(timezone=True),nullable=False))
    old=sa.Enum("OPEN","IN_PROGRESS","CLOSED","OVERDUE",name="history_old_status"); new=sa.Enum("OPEN","IN_PROGRESS","CLOSED","OVERDUE",name="history_new_status")
    op.create_table("status_history",sa.Column("history_id",sa.Integer(),primary_key=True),sa.Column("finding_id",sa.Integer(),sa.ForeignKey("findings.finding_id",ondelete="CASCADE"),nullable=False),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("old_status",old,nullable=False),sa.Column("new_status",new,nullable=False),sa.Column("changed_at",sa.DateTime(timezone=True),nullable=False),sa.Column("remarks",sa.Text()))
    op.create_table("attachments",sa.Column("attachment_id",sa.Integer(),primary_key=True),sa.Column("finding_id",sa.Integer(),sa.ForeignKey("findings.finding_id",ondelete="CASCADE"),nullable=False),sa.Column("file_name",sa.String(255),nullable=False),sa.Column("file_type",sa.String(100),nullable=False),sa.Column("file_path",sa.String(500),nullable=False))
    op.create_table("alerts",sa.Column("alert_id",sa.Integer(),primary_key=True),sa.Column("finding_id",sa.Integer(),sa.ForeignKey("findings.finding_id",ondelete="CASCADE"),nullable=False),sa.Column("alert_type",sa.String(100),nullable=False),sa.Column("recipient",sa.String(255),nullable=False),sa.Column("sent_date",sa.DateTime(timezone=True),nullable=False))
    op.create_table("finding_matches",sa.Column("match_id",sa.Integer(),primary_key=True),sa.Column("finding_id",sa.Integer(),sa.ForeignKey("findings.finding_id",ondelete="CASCADE"),nullable=False),sa.Column("previous_finding_id",sa.Integer(),sa.ForeignKey("findings.finding_id",ondelete="CASCADE"),nullable=False),sa.Column("similarity_score",sa.Float(),nullable=False),sa.Column("confirmed",sa.Boolean(),nullable=False,server_default=sa.false()),sa.UniqueConstraint("finding_id","previous_finding_id",name="uq_finding_match_pair"))


def downgrade() -> None:
    for table in ["finding_matches","alerts","attachments","status_history","audit_logs","remedial_actions","directives","findings","examinations","risk_outcomes","banks","users"]:
        op.drop_table(table)

