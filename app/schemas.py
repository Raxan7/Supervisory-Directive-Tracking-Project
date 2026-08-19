from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models import FindingStatus, Severity, UserRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    role: UserRole
    password: str = Field(min_length=10, max_length=128)


class UserRead(ORMModel):
    user_id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    role: UserRole | None = None
    is_active: bool | None = None


class BankCreate(BaseModel):
    bank_name: str
    bank_code: str
    bank_type: str


class BankRead(BankCreate, ORMModel):
    bank_id: int


class BankUpdate(BaseModel):
    bank_name: str | None = None
    bank_code: str | None = None
    bank_type: str | None = None


class ExaminationCreate(BaseModel):
    bank_id: int
    examination_type: str
    start_date: date
    end_date: date | None = None
    report_date: date | None = None
    examination_cycle: str


class ExaminationRead(ExaminationCreate, ORMModel):
    examination_id: int


class ExaminationUpdate(BaseModel):
    examination_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    report_date: date | None = None
    examination_cycle: str | None = None


class FindingCreate(BaseModel):
    examination_id: int
    bank_id: int
    title: str
    description: str
    risk_category: str
    severity: Severity
    deadline: date


class FindingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    risk_category: str | None = None
    severity: Severity | None = None
    deadline: date | None = None


class FindingStatusUpdate(BaseModel):
    status: FindingStatus
    remarks: str | None = None


class FindingRead(FindingCreate, ORMModel):
    finding_id: int
    examiner_id: int
    status: FindingStatus
    date_closed: date | None
    repeat_flag: bool
    chronic_flag: bool


class DirectiveCreate(BaseModel):
    directive_title: str
    deadline: date


class DirectiveRead(DirectiveCreate, ORMModel):
    directive_id: int
    finding_id: int
    status: FindingStatus


class DirectiveUpdate(BaseModel):
    directive_title: str | None = None
    deadline: date | None = None
    status: FindingStatus | None = None


class RemedialActionCreate(BaseModel):
    action_description: str
    deadline: date


class RemedialActionRead(RemedialActionCreate, ORMModel):
    action_id: int
    directive_id: int
    status: FindingStatus
    completion_date: date | None


class RemedialActionUpdate(BaseModel):
    action_description: str | None = None
    deadline: date | None = None
    status: FindingStatus | None = None
    completion_date: date | None = None


class RiskOutcomeCreate(BaseModel):
    bank_id: int
    risk_category: str
    risk_rating: str
    assessment_date: date


class RiskOutcomeRead(RiskOutcomeCreate, ORMModel):
    risk_outcome_id: int


class RiskOutcomeUpdate(BaseModel):
    risk_category: str | None = None
    risk_rating: str | None = None
    assessment_date: date | None = None


class DashboardSummary(BaseModel):
    total_findings: int
    open_findings: int
    in_progress_findings: int
    closed_findings: int
    overdue_findings: int
    repeated_findings: int
    chronic_findings: int
    closure_rate: float


class ImportResult(BaseModel):
    source_file: str
    accepted_rows: int
    rejected_rows: int
    errors: list[str]


class AttachmentRead(ORMModel):
    attachment_id: int
    finding_id: int | None
    examination_id: int | None
    bank_id: int | None
    file_name: str
    file_type: str
    file_path: str


class AuditLogRead(ORMModel):
    audit_id: int
    user_id: int
    action: str
    entity: str
    entity_id: int
    timestamp: datetime


class StatusHistoryRead(ORMModel):
    history_id: int
    finding_id: int
    user_id: int
    old_status: FindingStatus
    new_status: FindingStatus
    changed_at: datetime
    remarks: str | None


class FindingMatchRead(ORMModel):
    match_id: int
    finding_id: int
    previous_finding_id: int
    similarity_score: float
    confirmed: bool


class RiskLinkRow(BaseModel):
    bank_id: int
    bank_name: str
    total_findings: int
    closed_findings: int
    closure_rate: float
    average_days_to_close: float | None
    latest_risk_rating: str | None
    latest_assessment_date: date | None


class AlertRunResult(BaseModel):
    overdue_marked: int
    alerts_created: int
    emails_sent: int
    email_failures: int
