from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from app import models, schemas
from app.core.config import Settings
from app.emailer import send_email
from app.importers import parse_findings_document


def audit(db: Session, user_id: int, action: str, entity: str, entity_id: int) -> None:
    db.add(models.AuditLog(user_id=user_id, action=action, entity=entity, entity_id=entity_id))


def create_finding(db: Session, payload: schemas.FindingCreate, examiner: models.User) -> models.Finding:
    examination = db.get(models.Examination, payload.examination_id)
    if examination is None or examination.bank_id != payload.bank_id:
        raise ValueError("Examination does not belong to the selected bank")
    finding = models.Finding(**payload.model_dump(), examiner_id=examiner.user_id)
    db.add(finding); db.flush()
    audit(db, examiner.user_id, "create", "finding", finding.finding_id)
    db.commit(); db.refresh(finding)
    detect_repeated_findings(db, finding)
    db.refresh(finding)
    return finding


def change_finding_status(db: Session, finding: models.Finding, payload: schemas.FindingStatusUpdate, user: models.User) -> models.Finding:
    old = finding.status
    if payload.status == models.FindingStatus.CLOSED and old not in {models.FindingStatus.IN_PROGRESS, models.FindingStatus.OVERDUE}:
        raise ValueError("A finding must be in progress or overdue before it can be closed")
    finding.status = payload.status
    finding.date_closed = date.today() if payload.status == models.FindingStatus.CLOSED else None
    db.add(models.StatusHistory(finding_id=finding.finding_id, user_id=user.user_id, old_status=old, new_status=payload.status, remarks=payload.remarks))
    audit(db, user.user_id, "status_change", "finding", finding.finding_id)
    db.commit(); db.refresh(finding)
    return finding


def mark_overdue_findings(db: Session) -> int:
    findings = db.scalars(select(models.Finding).where(models.Finding.deadline < date.today(), models.Finding.status.in_([models.FindingStatus.OPEN, models.FindingStatus.IN_PROGRESS]))).all()
    for item in findings:
        item.status = models.FindingStatus.OVERDUE
    db.commit()
    return len(findings)


def dashboard_summary(db: Session, bank_id: int | None = None) -> schemas.DashboardSummary:
    query = select(
        func.count(models.Finding.finding_id),
        func.sum(case((models.Finding.status == models.FindingStatus.OPEN, 1), else_=0)),
        func.sum(case((models.Finding.status == models.FindingStatus.IN_PROGRESS, 1), else_=0)),
        func.sum(case((models.Finding.status == models.FindingStatus.CLOSED, 1), else_=0)),
        func.sum(case((models.Finding.status == models.FindingStatus.OVERDUE, 1), else_=0)),
        func.sum(case((models.Finding.repeat_flag.is_(True), 1), else_=0)),
        func.sum(case((models.Finding.chronic_flag.is_(True), 1), else_=0)),
    )
    if bank_id is not None:
        query = query.where(models.Finding.bank_id == bank_id)
    row = db.execute(query).one()
    total, opened, progress, closed, overdue, repeated, chronic = [int(value or 0) for value in row]
    return schemas.DashboardSummary(total_findings=total, open_findings=opened, in_progress_findings=progress, closed_findings=closed, overdue_findings=overdue, repeated_findings=repeated, chronic_findings=chronic, closure_rate=round(closed / total, 4) if total else 0.0)


def detect_repeated_findings(db: Session, finding: models.Finding, threshold: float = 0.72) -> list[models.FindingMatch]:
    previous = db.scalars(select(models.Finding).where(models.Finding.bank_id == finding.bank_id, models.Finding.finding_id != finding.finding_id)).all()
    matches = []
    candidate_text = f"{finding.title} {finding.description}".lower()
    for prior in previous:
        score = SequenceMatcher(None, candidate_text, f"{prior.title} {prior.description}".lower()).ratio()
        if score >= threshold:
            existing = db.scalar(select(models.FindingMatch).where(models.FindingMatch.finding_id == finding.finding_id, models.FindingMatch.previous_finding_id == prior.finding_id))
            if existing:
                existing.similarity_score = score
                matches.append(existing)
                continue
            match = models.FindingMatch(finding_id=finding.finding_id, previous_finding_id=prior.finding_id, similarity_score=score)
            db.add(match); matches.append(match)
    finding.repeat_flag = bool(matches)
    finding.chronic_flag = len(matches) >= 2
    db.commit()
    return matches


def pending_deadline_alerts(db: Session, within_days: int = 7) -> list[models.Finding]:
    end = date.today() + timedelta(days=within_days)
    return list(db.scalars(select(models.Finding).where(models.Finding.deadline <= end, models.Finding.status != models.FindingStatus.CLOSED)).all())


def import_findings_document(db: Session, content: bytes, filename: str, examiner: models.User) -> schemas.ImportResult:
    try:
        rows = parse_findings_document(filename, content)
    except Exception as exc:
        return schemas.ImportResult(source_file=filename, accepted_rows=0, rejected_rows=0, errors=[str(exc)])
    required = {"examination_id", "bank_id", "title", "description", "risk_category", "severity", "deadline"}
    available = set(rows[0]) if rows else set()
    if not required.issubset(available):
        return schemas.ImportResult(source_file=filename, accepted_rows=0, rejected_rows=0, errors=[f"Required columns: {', '.join(sorted(required))}"])
    accepted = 0; errors = []; imported_ids: list[int] = []
    for line, row in enumerate(rows, start=2):
        try:
            with db.begin_nested():
                raw_deadline = row["deadline"]
                parsed_deadline = raw_deadline.date() if isinstance(raw_deadline, datetime) else (raw_deadline if isinstance(raw_deadline, date) else date.fromisoformat(str(raw_deadline).strip()))
                payload = schemas.FindingCreate(examination_id=int(row["examination_id"]), bank_id=int(row["bank_id"]), title=str(row["title"]).strip(), description=str(row["description"]).strip(), risk_category=str(row["risk_category"]).strip(), severity=models.Severity(str(row["severity"]).strip().lower()), deadline=parsed_deadline)
                examination = db.get(models.Examination, payload.examination_id)
                if examination is None or examination.bank_id != payload.bank_id:
                    raise ValueError("Examination does not belong to the selected bank")
                item = models.Finding(**payload.model_dump(), examiner_id=examiner.user_id)
                db.add(item); db.flush(); audit(db, examiner.user_id, "import", "finding", item.finding_id); imported_ids.append(item.finding_id); accepted += 1
        except Exception as exc:
            errors.append(f"Row {line}: {exc}")
    if accepted:
        db.commit()
        for finding_id in imported_ids:
            detect_repeated_findings(db, db.get(models.Finding, finding_id))
    else:
        db.rollback()
    return schemas.ImportResult(source_file=filename, accepted_rows=accepted, rejected_rows=len(errors), errors=errors)


def process_deadline_alerts(db: Session, settings: Settings) -> schemas.AlertRunResult:
    overdue_marked = mark_overdue_findings(db)
    candidates = pending_deadline_alerts(db, settings.alert_days_before)
    created = sent = failures = 0
    today = date.today()
    for finding in candidates:
        alert_type = "overdue" if finding.deadline < today else "deadline_approaching"
        already = db.scalar(select(models.Alert).where(models.Alert.finding_id == finding.finding_id, models.Alert.alert_type == alert_type, func.date(models.Alert.sent_date) == today))
        if already:
            continue
        recipient = finding.examiner.email
        alert = models.Alert(finding_id=finding.finding_id, alert_type=alert_type, recipient=recipient)
        db.add(alert); created += 1
        subject = f"Supervisory finding {alert_type.replace('_', ' ')}: {finding.title}"
        body = f"Finding #{finding.finding_id} for bank #{finding.bank_id} has deadline {finding.deadline.isoformat()} and status {finding.status.value}."
        try:
            if send_email(settings, recipient, subject, body):
                sent += 1
        except Exception:
            failures += 1
    db.commit()
    return schemas.AlertRunResult(overdue_marked=overdue_marked, alerts_created=created, emails_sent=sent, email_failures=failures)


def risk_link_analytics(db: Session, bank_id: int | None = None) -> list[schemas.RiskLinkRow]:
    banks = db.scalars(select(models.Bank).where(models.Bank.bank_id == bank_id) if bank_id else select(models.Bank).order_by(models.Bank.bank_name)).all()
    result = []
    for bank in banks:
        findings = db.scalars(select(models.Finding).where(models.Finding.bank_id == bank.bank_id)).all()
        closed = [f for f in findings if f.status == models.FindingStatus.CLOSED]
        durations = [(f.date_closed - f.examination.start_date).days for f in closed if f.date_closed and f.examination]
        latest = db.scalar(select(models.RiskOutcome).where(models.RiskOutcome.bank_id == bank.bank_id).order_by(models.RiskOutcome.assessment_date.desc()).limit(1))
        result.append(schemas.RiskLinkRow(bank_id=bank.bank_id, bank_name=bank.bank_name, total_findings=len(findings), closed_findings=len(closed), closure_rate=round(len(closed)/len(findings),4) if findings else 0.0, average_days_to_close=round(sum(durations)/len(durations),2) if durations else None, latest_risk_rating=latest.risk_rating if latest else None, latest_assessment_date=latest.assessment_date if latest else None))
    return result
