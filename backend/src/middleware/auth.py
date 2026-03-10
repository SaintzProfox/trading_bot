"""JWT Authentication middleware"""

import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET = os.getenv("JWT_SECRET", "change-me")
ALGORITHM = "HS256"

bearer_scheme = HTTPBearer()


def create_token(user_id: int, email: str, role: str = "user") -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def verify_token(token: Optional[str] = None, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    raw = token or (credentials.credentials if credentials else None)
    if not raw:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(raw, SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(payload: dict = Depends(verify_token)) -> dict:
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return payload
