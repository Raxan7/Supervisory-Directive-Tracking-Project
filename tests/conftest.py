import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"]="sqlite:///./test-supervisory.db"
os.environ["ALERT_SCAN_SECONDS"]="3600"
os.environ["BOOTSTRAP_ADMIN_EMAIL"]=""
os.environ["BOOTSTRAP_ADMIN_PASSWORD"]=""

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402
from app.core.security import hash_password  # noqa: E402

engine=create_engine("sqlite:///./test-supervisory.db",connect_args={"check_same_thread":False})
TestingSession=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)


def override_db():
    db=TestingSession()
    try: yield db
    finally: db.close()


app.dependency_overrides[get_db]=override_db


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add_all([
            User(full_name="Admin User",email="admin@example.org",role=UserRole.ADMIN,password_hash=hash_password("Admin-password-123")),
            User(full_name="Examiner User",email="examiner@example.org",role=UserRole.EXAMINER,password_hash=hash_password("Examiner-password-123")),
            User(full_name="Manager User",email="manager@example.org",role=UserRole.MANAGER,password_hash=hash_password("Manager-password-123")),
        ]); db.commit()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client: yield test_client


def token(client, email, password):
    response=client.post("/api/v1/auth/login",json={"email":email,"password":password})
    assert response.status_code==200,response.text
    return {"Authorization":f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def examiner_headers(client): return token(client,"examiner@example.org","Examiner-password-123")


@pytest.fixture
def manager_headers(client): return token(client,"manager@example.org","Manager-password-123")


@pytest.fixture
def admin_headers(client): return token(client,"admin@example.org","Admin-password-123")
