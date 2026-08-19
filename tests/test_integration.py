from datetime import date, timedelta
from io import BytesIO
from docx import Document


def seed_bank_exam(client, headers):
    bank=client.post("/api/v1/banks",headers=headers,json={"bank_name":"Example Bank","bank_code":"EXB","bank_type":"Commercial"})
    assert bank.status_code==201,bank.text
    exam=client.post("/api/v1/examinations",headers=headers,json={"bank_id":bank.json()["bank_id"],"examination_type":"On-site","start_date":"2026-01-05","end_date":"2026-01-20","report_date":"2026-02-01","examination_cycle":"2026-Q1"})
    assert exam.status_code==201,exam.text
    return bank.json(),exam.json()


def test_complete_finding_workflow(client, examiner_headers, manager_headers):
    bank,exam=seed_bank_exam(client,examiner_headers)
    finding=client.post("/api/v1/findings",headers=examiner_headers,json={"examination_id":exam["examination_id"],"bank_id":bank["bank_id"],"title":"Weak credit controls","description":"Credit approval exceptions were not reviewed.","risk_category":"Credit Risk","severity":"high","deadline":(date.today()+timedelta(days=10)).isoformat()})
    assert finding.status_code==201,finding.text; fid=finding.json()["finding_id"]
    assert client.patch(f"/api/v1/findings/{fid}",headers=examiner_headers,json={"title":"Weak credit approval controls"}).status_code==200
    directive=client.post(f"/api/v1/findings/{fid}/directives",headers=examiner_headers,json={"directive_title":"Strengthen exception review","deadline":(date.today()+timedelta(days=20)).isoformat()})
    assert directive.status_code==201
    action=client.post(f"/api/v1/directives/{directive.json()['directive_id']}/actions",headers=examiner_headers,json={"action_description":"Implement weekly exception review","deadline":(date.today()+timedelta(days=15)).isoformat()})
    assert action.status_code==201
    assert client.patch(f"/api/v1/findings/{fid}/status",headers=examiner_headers,json={"status":"in_progress","remarks":"Bank submitted a plan"}).status_code==200
    closed=client.patch(f"/api/v1/findings/{fid}/status",headers=examiner_headers,json={"status":"closed","remarks":"Evidence verified"})
    assert closed.status_code==200 and closed.json()["date_closed"]
    dashboard=client.get("/api/v1/analytics/dashboard",headers=manager_headers)
    assert dashboard.status_code==200 and dashboard.json()["closed_findings"]==1
    history=client.get(f"/api/v1/findings/{fid}/status-history",headers=manager_headers)
    assert len(history.json())==2


def test_docx_import_stores_attachment(client, examiner_headers, manager_headers):
    bank,exam=seed_bank_exam(client,examiner_headers)
    doc=Document(); doc.add_paragraph("Examination report findings")
    buf=BytesIO(); doc.save(buf)
    imported=client.post("/api/v1/imports/findings",headers=examiner_headers,files={"file":("report.docx",buf.getvalue(),"application/vnd.openxmlformats-officedocument.wordprocessingml.document")},params={"examination_id":exam["examination_id"],"bank_id":bank["bank_id"]})
    assert imported.status_code==201,imported.text
    data=imported.json()
    assert data["examination_id"]==exam["examination_id"]
    assert data["bank_id"]==bank["bank_id"]
    assert data["finding_id"] is None
    assert client.get(f"/api/v1/attachments/{data['attachment_id']}/download",headers=examiner_headers).status_code==200
    run=client.post("/api/v1/alerts/run",headers=manager_headers)
    assert run.status_code==200
    report=client.get("/api/v1/reports/findings.csv",headers=manager_headers)
    assert report.status_code==200


def test_role_enforcement_and_audit_access(client, examiner_headers, admin_headers):
    assert client.get("/api/v1/audit-logs",headers=examiner_headers).status_code==403
    assert client.get("/api/v1/audit-logs",headers=admin_headers).status_code==200
    assert client.post("/api/v1/users",headers=examiner_headers,json={"full_name":"No Access","email":"no@example.org","role":"manager","password":"Long-password-123"}).status_code==403
