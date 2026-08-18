import getpass
from sqlalchemy import select
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import User, UserRole


def main():
    email=input("Admin email: ").strip().lower(); full_name=input("Full name: ").strip(); password=getpass.getpass("Password (10+ characters): ")
    if len(password)<10: raise SystemExit("Password is too short")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email==email)): raise SystemExit("User already exists")
        db.add(User(email=email,full_name=full_name,role=UserRole.ADMIN,password_hash=hash_password(password))); db.commit()
    print("Administrator created")


if __name__=="__main__": main()

