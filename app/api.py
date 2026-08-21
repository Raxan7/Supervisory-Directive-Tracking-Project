import csv
import io
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from app import models, schemas, services
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import CurrentUser, DB, allow_roles
from app.storage import upload_file, download_file

router = APIRouter(prefix="/api/v1")


@router.post("/auth/login", response_model=schemas.Token, tags=["Authentication"])
def login(payload: schemas.LoginRequest, db: DB):
    user = db.scalar(select(models.User).where(models.User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    settings = get_settings()
    return schemas.Token(access_token=create_access_token(str(user.user_id), user.role.value, settings.secret_key, timedelta(minutes=settings.access_token_minutes)))


@router.post("/users", response_model=schemas.UserRead, status_code=201, tags=["User Administration"])
def create_user(payload: schemas.UserCreate, db: DB, admin=Depends(allow_roles(models.UserRole.ADMIN))):
    if db.scalar(select(models.User).where(models.User.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = models.User(full_name=payload.full_name, email=payload.email, role=payload.role, password_hash=hash_password(payload.password))
    db.add(user); db.flush(); services.audit(db, admin.user_id, "create", "user", user.user_id); db.commit(); db.refresh(user)
    return user


@router.get("/users", response_model=list[schemas.UserRead], tags=["User Administration"])
def list_users(db: DB, _=Depends(allow_roles(models.UserRole.ADMIN))):
    return list(db.scalars(select(models.User).order_by(models.User.full_name)).all())


@router.get("/users/me", response_model=schemas.UserRead, tags=["Authentication"])
def get_me(user: CurrentUser):
    return user


@router.patch("/users/{user_id}", response_model=schemas.UserRead, tags=["User Administration"])
def update_user(user_id: int, payload: schemas.UserUpdate, db: DB, admin=Depends(allow_roles(models.UserRole.ADMIN))):
    user=db.get(models.User,user_id)
    if not user: raise HTTPException(404,"User not found")
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(user,key,value)
    services.audit(db,admin.user_id,"update","user",user.user_id); db.commit(); db.refresh(user); return user


@router.post("/banks", response_model=schemas.BankRead, status_code=201, tags=["Examination Management"])
def create_bank(payload: schemas.BankCreate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER, models.UserRole.ADMIN))):
    bank = models.Bank(**payload.model_dump()); db.add(bank); db.flush(); services.audit(db, user.user_id, "create", "bank", bank.bank_id); db.commit(); db.refresh(bank); return bank


@router.get("/banks", response_model=list[schemas.BankRead], tags=["Examination Management"])
def list_banks(db: DB, _: CurrentUser):
    return list(db.scalars(select(models.Bank).order_by(models.Bank.bank_name)).all())


@router.patch("/banks/{bank_id}", response_model=schemas.BankRead, tags=["Examination Management"])
def update_bank(bank_id: int, payload: schemas.BankUpdate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER, models.UserRole.ADMIN))):
    bank=db.get(models.Bank,bank_id)
    if not bank: raise HTTPException(404,"Bank not found")
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(bank,key,value)
    services.audit(db,user.user_id,"update","bank",bank_id); db.commit(); db.refresh(bank); return bank


@router.post("/examinations", response_model=schemas.ExaminationRead, status_code=201, tags=["Examination Management"])
def create_examination(payload: schemas.ExaminationCreate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER, models.UserRole.ADMIN))):
    if not db.get(models.Bank, payload.bank_id):
        raise HTTPException(404, "Bank not found")
    examination = models.Examination(**payload.model_dump())
    db.add(examination)
    db.flush()
    services.audit(db, user.user_id, "create", "examination", examination.examination_id)
    db.commit()
    db.refresh(examination)
    return examination


@router.get("/examinations", response_model=list[schemas.ExaminationRead], tags=["Examination Management"])
def list_examinations(db: DB, _: CurrentUser, bank_id: int | None = None):
    query = select(models.Examination).order_by(models.Examination.start_date.desc())
    if bank_id: query = query.where(models.Examination.bank_id == bank_id)
    return list(db.scalars(query).all())


@router.patch("/examinations/{examination_id}", response_model=schemas.ExaminationRead, tags=["Examination Management"])
def update_examination(examination_id: int, payload: schemas.ExaminationUpdate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER, models.UserRole.ADMIN))):
    item=db.get(models.Examination,examination_id)
    if not item: raise HTTPException(404,"Examination not found")
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(item,key,value)
    services.audit(db,user.user_id,"update","examination",examination_id); db.commit(); db.refresh(item); return item


@router.post("/risk-outcomes", response_model=schemas.RiskOutcomeRead, status_code=201, tags=["Risk Outcomes"])
def create_risk_outcome(payload: schemas.RiskOutcomeCreate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER, models.UserRole.ADMIN))):
    if not db.get(models.Bank, payload.bank_id): raise HTTPException(404, "Bank not found")
    item=models.RiskOutcome(**payload.model_dump()); db.add(item); db.flush(); services.audit(db,user.user_id,"create","risk_outcome",item.risk_outcome_id); db.commit(); db.refresh(item); return item


@router.get("/risk-outcomes", response_model=list[schemas.RiskOutcomeRead], tags=["Risk Outcomes"])
def list_risk_outcomes(db: DB, _: CurrentUser, bank_id: int | None = None):
    query=select(models.RiskOutcome).order_by(models.RiskOutcome.assessment_date.desc())
    if bank_id: query=query.where(models.RiskOutcome.bank_id==bank_id)
    return list(db.scalars(query).all())


@router.patch("/risk-outcomes/{risk_outcome_id}", response_model=schemas.RiskOutcomeRead, tags=["Risk Outcomes"])
def update_risk_outcome(risk_outcome_id: int, payload: schemas.RiskOutcomeUpdate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER, models.UserRole.ADMIN))):
    item=db.get(models.RiskOutcome,risk_outcome_id)
    if not item: raise HTTPException(404,"Risk outcome not found")
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(item,key,value)
    services.audit(db,user.user_id,"update","risk_outcome",risk_outcome_id); db.commit(); db.refresh(item); return item


@router.post("/findings", response_model=schemas.FindingRead, status_code=201, tags=["Findings & Directives"])
def create_finding(payload: schemas.FindingCreate, db: DB, examiner=Depends(allow_roles(models.UserRole.EXAMINER))):
    try: return services.create_finding(db, payload, examiner)
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/findings", response_model=list[schemas.FindingRead], tags=["Findings & Directives"])
def list_findings(db: DB, _: CurrentUser, bank_id: int | None = None, finding_status: models.FindingStatus | None = Query(None, alias="status"), risk_category: str | None = None, overdue_only: bool = False, limit: int = Query(100,ge=1,le=500), offset: int = Query(0,ge=0)):
    query = select(models.Finding).order_by(models.Finding.deadline)
    if bank_id: query = query.where(models.Finding.bank_id == bank_id)
    if finding_status: query = query.where(models.Finding.status == finding_status)
    if risk_category: query = query.where(models.Finding.risk_category == risk_category)
    if overdue_only: query = query.where(models.Finding.deadline < __import__('datetime').date.today(), models.Finding.status != models.FindingStatus.CLOSED)
    return list(db.scalars(query.offset(offset).limit(limit)).all())


@router.get("/findings/{finding_id}", response_model=schemas.FindingRead, tags=["Findings & Directives"])
def get_finding(finding_id: int, db: DB, _: CurrentUser):
    item=db.get(models.Finding,finding_id)
    if not item: raise HTTPException(404,"Finding not found")
    return item


@router.patch("/findings/{finding_id}", response_model=schemas.FindingRead, tags=["Findings & Directives"])
def edit_finding(finding_id: int, payload: schemas.FindingUpdate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER))):
    item=db.get(models.Finding,finding_id)
    if not item: raise HTTPException(404,"Finding not found")
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(item,key,value)
    services.audit(db,user.user_id,"update","finding",finding_id); db.commit(); db.refresh(item); return item


@router.patch("/findings/{finding_id}/status", response_model=schemas.FindingRead, tags=["Findings & Directives"])
def update_finding_status(finding_id: int, payload: schemas.FindingStatusUpdate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER))):
    finding = db.get(models.Finding, finding_id)
    if not finding: raise HTTPException(404, "Finding not found")
    try: return services.change_finding_status(db, finding, payload, user)
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.post("/findings/{finding_id}/directives", response_model=schemas.DirectiveRead, status_code=201, tags=["Findings & Directives"])
def create_directive(finding_id: int, payload: schemas.DirectiveCreate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER))):
    if not db.get(models.Finding, finding_id): raise HTTPException(404, "Finding not found")
    item=models.Directive(finding_id=finding_id, **payload.model_dump()); db.add(item); db.flush(); services.audit(db,user.user_id,"create","directive",item.directive_id); db.commit(); db.refresh(item); return item


@router.get("/findings/{finding_id}/directives", response_model=list[schemas.DirectiveRead], tags=["Findings & Directives"])
def list_directives(finding_id: int, db: DB, _: CurrentUser):
    return list(db.scalars(select(models.Directive).where(models.Directive.finding_id==finding_id).order_by(models.Directive.deadline)).all())


@router.patch("/directives/{directive_id}", response_model=schemas.DirectiveRead, tags=["Findings & Directives"])
def update_directive(directive_id: int, payload: schemas.DirectiveUpdate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER))):
    item=db.get(models.Directive,directive_id)
    if not item: raise HTTPException(404,"Directive not found")
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(item,key,value)
    services.audit(db,user.user_id,"update","directive",directive_id); db.commit(); db.refresh(item); return item


@router.post("/directives/{directive_id}/actions", response_model=schemas.RemedialActionRead, status_code=201, tags=["Remedial Action Tracking"])
def create_action(directive_id: int, payload: schemas.RemedialActionCreate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER))):
    if not db.get(models.Directive, directive_id): raise HTTPException(404, "Directive not found")
    item=models.RemedialAction(directive_id=directive_id, **payload.model_dump()); db.add(item); db.flush(); services.audit(db,user.user_id,"create","remedial_action",item.action_id); db.commit(); db.refresh(item); return item


@router.get("/directives/{directive_id}/actions", response_model=list[schemas.RemedialActionRead], tags=["Remedial Action Tracking"])
def list_actions(directive_id: int, db: DB, _: CurrentUser):
    return list(db.scalars(select(models.RemedialAction).where(models.RemedialAction.directive_id==directive_id).order_by(models.RemedialAction.deadline)).all())


@router.patch("/actions/{action_id}", response_model=schemas.RemedialActionRead, tags=["Remedial Action Tracking"])
def update_action(action_id: int, payload: schemas.RemedialActionUpdate, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER))):
    item=db.get(models.RemedialAction,action_id)
    if not item: raise HTTPException(404,"Remedial action not found")
    values=payload.model_dump(exclude_unset=True)
    if values.get("status")==models.FindingStatus.CLOSED and "completion_date" not in values: values["completion_date"]=date.today()
    for key,value in values.items(): setattr(item,key,value)
    services.audit(db,user.user_id,"update","remedial_action",action_id); db.commit(); db.refresh(item); return item


@router.post("/imports/findings", response_model=schemas.AttachmentRead, status_code=201, tags=["Document Import"])
async def import_findings(db: DB, examiner=Depends(allow_roles(models.UserRole.EXAMINER)), file: UploadFile = File(...), examination_id: int = Query(...), bank_id: int = Query(...)):
    content=await file.read(); settings=get_settings()
    if len(content)>settings.max_upload_bytes: raise HTTPException(413,"File exceeds configured upload limit")
    if not db.get(models.Examination, examination_id): raise HTTPException(404,"Examination not found")
    if not db.get(models.Bank, bank_id): raise HTTPException(404,"Bank not found")
    suffix=Path(file.filename or "").suffix.lower()
    if suffix not in {".docx", ".pdf", ".xlsx", ".xls"}: raise HTTPException(422,"Only DOCX, PDF, and Excel files are accepted")
    original=Path(file.filename or "upload").name
    safe=re.sub(r"[^A-Za-z0-9._-]","_",original)
    object_key=f"examinations/{examination_id}/{uuid4().hex}_{safe}"
    upload_file(object_key, content, file.content_type or "application/octet-stream")
    item=models.Attachment(examination_id=examination_id,bank_id=bank_id,file_name=original,file_type=file.content_type or "application/octet-stream",file_path=object_key)
    db.add(item); db.flush(); services.audit(db,examiner.user_id,"upload","attachment",item.attachment_id); db.commit(); db.refresh(item); return item


@router.get("/attachments/{attachment_id}/download", tags=["Document Storage"])
def download_attachment(attachment_id: int, db: DB, _: CurrentUser):
    item=db.get(models.Attachment,attachment_id)
    if not item: raise HTTPException(404,"Attachment not found")
    content=download_file(item.file_path)
    if content is None: raise HTTPException(404,"File not found")
    return StreamingResponse(iter([content]),media_type=item.file_type,headers={"Content-Disposition":f'attachment; filename="{item.file_name}"'})


@router.post("/findings/{finding_id}/detect-repeats", tags=["AI / ML Analytics"])
def detect_repeats(finding_id: int, db: DB, _=Depends(allow_roles(models.UserRole.EXAMINER, models.UserRole.MANAGER))):
    finding=db.get(models.Finding,finding_id)
    if not finding: raise HTTPException(404,"Finding not found")
    matches=services.detect_repeated_findings(db,finding)
    return {"finding_id":finding_id,"matches":[{"previous_finding_id":m.previous_finding_id,"similarity_score":round(m.similarity_score,4)} for m in matches]}


@router.patch("/finding-matches/{match_id}/confirm", response_model=schemas.FindingMatchRead, tags=["AI / ML Analytics"])
def confirm_match(match_id: int, db: DB, user=Depends(allow_roles(models.UserRole.EXAMINER, models.UserRole.MANAGER))):
    item=db.get(models.FindingMatch,match_id)
    if not item: raise HTTPException(404,"Finding match not found")
    item.confirmed=True; services.audit(db,user.user_id,"confirm","finding_match",match_id); db.commit(); db.refresh(item); return item


@router.get("/analytics/dashboard", response_model=schemas.DashboardSummary, tags=["Dashboard & Reporting"])
def dashboard(db: DB, _: CurrentUser, bank_id: int | None = None):
    services.mark_overdue_findings(db)
    return services.dashboard_summary(db, bank_id)


@router.get("/analytics/risk-link", response_model=list[schemas.RiskLinkRow], tags=["Dashboard & Reporting"])
def risk_link(db: DB, _: CurrentUser, bank_id: int | None=None):
    return services.risk_link_analytics(db,bank_id)


@router.get("/alerts/pending", response_model=list[schemas.FindingRead], tags=["Deadline & Alerts"])
def pending_alerts(db: DB, _: CurrentUser, within_days: int = Query(7, ge=0, le=90)):
    return services.pending_deadline_alerts(db, within_days)


@router.post("/alerts/run", response_model=schemas.AlertRunResult, tags=["Deadline & Alerts"])
def run_alerts(db: DB, _=Depends(allow_roles(models.UserRole.MANAGER,models.UserRole.ADMIN))):
    return services.process_deadline_alerts(db,get_settings())


@router.get("/audit-logs", response_model=list[schemas.AuditLogRead], tags=["Audit Logging"])
def list_audit_logs(db: DB, _=Depends(allow_roles(models.UserRole.ADMIN)), entity: str | None=None, user_id: int | None=None, limit: int=Query(200,ge=1,le=1000)):
    query=select(models.AuditLog).order_by(models.AuditLog.timestamp.desc())
    if entity: query=query.where(models.AuditLog.entity==entity)
    if user_id: query=query.where(models.AuditLog.user_id==user_id)
    return list(db.scalars(query.limit(limit)).all())


@router.get("/findings/{finding_id}/status-history", response_model=list[schemas.StatusHistoryRead], tags=["Findings & Directives"])
def status_history(finding_id: int, db: DB, _: CurrentUser):
    return list(db.scalars(select(models.StatusHistory).where(models.StatusHistory.finding_id==finding_id).order_by(models.StatusHistory.changed_at)).all())


@router.get("/reports/findings.csv", tags=["Dashboard & Reporting"])
def export_findings(db: DB, _: CurrentUser, bank_id: int | None=None):
    query=select(models.Finding).order_by(models.Finding.bank_id,models.Finding.deadline)
    if bank_id: query=query.where(models.Finding.bank_id==bank_id)
    output=io.StringIO(); writer=csv.writer(output); writer.writerow(["finding_id","bank_id","examination_id","title","risk_category","severity","deadline","status","repeat_flag","chronic_flag"])
    for f in db.scalars(query): writer.writerow([f.finding_id,f.bank_id,f.examination_id,f.title,f.risk_category,f.severity.value,f.deadline.isoformat(),f.status.value,f.repeat_flag,f.chronic_flag])
    return StreamingResponse(iter([output.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=findings-report.csv"})
