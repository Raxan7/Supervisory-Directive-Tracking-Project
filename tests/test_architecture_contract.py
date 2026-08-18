import ast
from pathlib import Path

ROOT=Path(__file__).parents[1]


def test_original_twelve_models_are_present():
    tree=ast.parse((ROOT/"app/models.py").read_text())
    classes={node.name for node in tree.body if isinstance(node,ast.ClassDef)}
    expected={"User","Bank","RiskOutcome","Examination","Finding","Directive","RemedialAction","AuditLog","StatusHistory","Attachment","Alert","FindingMatch"}
    assert expected <= classes


def test_fastapi_entrypoint_and_architecture_routes_exist():
    main=(ROOT/"app/main.py").read_text(); api=(ROOT/"app/api.py").read_text()
    assert "FastAPI(" in main
    for route in ["/auth/login","/users","/banks","/examinations","/risk-outcomes","/findings","/imports/findings","/analytics/dashboard","/alerts/pending"]:
        assert route in api


def test_original_finding_states_are_exact():
    models=(ROOT/"app/models.py").read_text()
    for state in ["OPEN", "IN_PROGRESS", "CLOSED", "OVERDUE"]:
        assert f'{state} = ' in models
