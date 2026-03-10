"""Authentication routes — login, register, refresh"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
import bcrypt
from src.middleware.auth import create_token

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    db = request.app.state.db
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", body.email)
    if not user or not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["id"], user["email"], user["role"])
    return {"access_token": token, "token_type": "bearer", "user": {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]}}


@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    db = request.app.state.db
    existing = await db.fetchrow("SELECT id FROM users WHERE email = $1", body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = await db.fetchrow(
        "INSERT INTO users (email, password_hash, name, role) VALUES ($1,$2,$3,'user') RETURNING id, email, name, role",
        body.email, pw_hash, body.name
    )
    token = create_token(user["id"], user["email"], user["role"])
    return {"access_token": token, "token_type": "bearer", "user": dict(user)}


@router.get("/me")
async def me(request: Request, payload: dict = None):
    from src.middleware.auth import verify_token
    from fastapi import Depends
    return {"user": payload}
