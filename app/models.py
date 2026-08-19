import enum
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class UserRole(str, enum.Enum):
    EXAMINER = "examiner"
    MANAGER = "manager"
    ADMIN = "admin"


class FindingStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    OVERDUE = "overdue"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    findings: Mapped[list["Finding"]] = relationship(back_populates="examiner")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class Bank(Base):
    __tablename__ = "banks"
    bank_id: Mapped[int] = mapped_column(primary_key=True)
    bank_name: Mapped[str] = mapped_column(String(180), unique=True)
    bank_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    bank_type: Mapped[str] = mapped_column(String(100))
    examinations: Mapped[list["Examination"]] = relationship(back_populates="bank")
    risk_outcomes: Mapped[list["RiskOutcome"]] = relationship(back_populates="bank")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="bank")


class RiskOutcome(Base):
    __tablename__ = "risk_outcomes"
    risk_outcome_id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.bank_id", ondelete="CASCADE"), index=True)
    risk_category: Mapped[str] = mapped_column(String(120), index=True)
    risk_rating: Mapped[str] = mapped_column(String(80))
    assessment_date: Mapped[date] = mapped_column(Date, index=True)
    bank: Mapped[Bank] = relationship(back_populates="risk_outcomes")


class Examination(Base):
    __tablename__ = "examinations"
    examination_id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.bank_id", ondelete="RESTRICT"), index=True)
    examination_type: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    report_date: Mapped[date | None] = mapped_column(Date)
    examination_cycle: Mapped[str] = mapped_column(String(80), index=True)
    bank: Mapped[Bank] = relationship(back_populates="examinations")
    findings: Mapped[list["Finding"]] = relationship(back_populates="examination")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="examination")


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (Index("ix_findings_bank_status_deadline", "bank_id", "status", "deadline"),)
    finding_id: Mapped[int] = mapped_column(primary_key=True)
    examination_id: Mapped[int] = mapped_column(ForeignKey("examinations.examination_id", ondelete="CASCADE"), index=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.bank_id", ondelete="RESTRICT"), index=True)
    examiner_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    risk_category: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="finding_severity"), index=True)
    deadline: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus, name="finding_status"), default=FindingStatus.OPEN, index=True)
    date_closed: Mapped[date | None] = mapped_column(Date)
    repeat_flag: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    chronic_flag: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    examination: Mapped[Examination] = relationship(back_populates="findings")
    examiner: Mapped[User] = relationship(back_populates="findings")
    directives: Mapped[list["Directive"]] = relationship(back_populates="finding", cascade="all, delete-orphan")
    status_history: Mapped[list["StatusHistory"]] = relationship(back_populates="finding", cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="finding", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="finding", cascade="all, delete-orphan")


class Directive(Base):
    __tablename__ = "directives"
    directive_id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.finding_id", ondelete="CASCADE"), index=True)
    directive_title: Mapped[str] = mapped_column(Text)
    deadline: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus, name="directive_status"), default=FindingStatus.OPEN)
    finding: Mapped[Finding] = relationship(back_populates="directives")
    remedial_actions: Mapped[list["RemedialAction"]] = relationship(back_populates="directive", cascade="all, delete-orphan")


class RemedialAction(Base):
    __tablename__ = "remedial_actions"
    action_id: Mapped[int] = mapped_column(primary_key=True)
    directive_id: Mapped[int] = mapped_column(ForeignKey("directives.directive_id", ondelete="CASCADE"), index=True)
    action_description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus, name="action_status"), default=FindingStatus.OPEN)
    completion_date: Mapped[date | None] = mapped_column(Date)
    directive: Mapped[Directive] = relationship(back_populates="remedial_actions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    audit_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[int] = mapped_column(index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    user: Mapped[User] = relationship(back_populates="audit_logs")


class StatusHistory(Base):
    __tablename__ = "status_history"
    history_id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.finding_id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), index=True)
    old_status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus, name="history_old_status"))
    new_status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus, name="history_new_status"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    remarks: Mapped[str | None] = mapped_column(Text)
    finding: Mapped[Finding] = relationship(back_populates="status_history")


class Attachment(Base):
    __tablename__ = "attachments"
    attachment_id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("findings.finding_id", ondelete="CASCADE"), index=True, nullable=True)
    examination_id: Mapped[int | None] = mapped_column(ForeignKey("examinations.examination_id", ondelete="CASCADE"), index=True, nullable=True)
    bank_id: Mapped[int | None] = mapped_column(ForeignKey("banks.bank_id", ondelete="CASCADE"), index=True, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(100))
    file_path: Mapped[str] = mapped_column(String(500))
    finding: Mapped[Finding | None] = relationship(back_populates="attachments")
    examination: Mapped[Examination | None] = relationship()
    bank: Mapped[Bank | None] = relationship()


class Alert(Base):
    __tablename__ = "alerts"
    alert_id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.finding_id", ondelete="CASCADE"), index=True)
    alert_type: Mapped[str] = mapped_column(String(100), index=True)
    recipient: Mapped[str] = mapped_column(String(255))
    sent_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finding: Mapped[Finding] = relationship(back_populates="alerts")


class FindingMatch(Base):
    __tablename__ = "finding_matches"
    __table_args__ = (UniqueConstraint("finding_id", "previous_finding_id", name="uq_finding_match_pair"),)
    match_id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.finding_id", ondelete="CASCADE"), index=True)
    previous_finding_id: Mapped[int] = mapped_column(ForeignKey("findings.finding_id", ondelete="CASCADE"), index=True)
    similarity_score: Mapped[float] = mapped_column(Float)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
