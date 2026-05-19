from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, RefreshToken
from ..schemas import UserCreate, UserLogin, Token, TokenRefresh, UserResponse
from ..auth import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


def _get_current_user(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
    return user


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    db.add(RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        username=user.username,
        user_id=user.id,
    )


@router.post("/refresh", response_model=Token)
def refresh(body: TokenRefresh, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다")

    rt = db.query(RefreshToken).filter(
        RefreshToken.token == body.refresh_token,
        RefreshToken.is_revoked == False,
    ).first()
    if not rt or rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="만료되었거나 취소된 토큰입니다")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")

    # 기존 토큰 폐기 후 새 토큰 발급 (rotation)
    rt.is_revoked = True
    new_access = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    db.add(RefreshToken(
        user_id=user.id,
        token=new_refresh,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        username=user.username,
        user_id=user.id,
    )


@router.post("/logout")
def logout(body: TokenRefresh, db: Session = Depends(get_db)):
    rt = db.query(RefreshToken).filter(RefreshToken.token == body.refresh_token).first()
    if rt:
        rt.is_revoked = True
        db.commit()
    return {"message": "로그아웃 되었습니다"}


@router.get("/me", response_model=UserResponse)
def me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    return _get_current_user(credentials, db)
