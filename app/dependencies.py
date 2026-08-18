from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db import get_db
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
DB = Annotated[Session, Depends(get_db)]


def current_user(db: DB, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    try:
        payload = decode_access_token(token, get_settings().secret_key)
        user = db.get(User, int(payload["sub"]))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials") from exc
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def allow_roles(*roles: UserRole):
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user
    return dependency

