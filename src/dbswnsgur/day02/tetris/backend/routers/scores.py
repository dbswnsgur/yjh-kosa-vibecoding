from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, Score
from ..schemas import ScoreCreate, ScoreResponse
from ..auth import decode_token

router = APIRouter(prefix="/scores", tags=["scores"])
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
    return user


@router.post("", response_model=ScoreResponse, status_code=201)
def save_score(
    body: ScoreCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = Score(user_id=user.id, score=body.score, level=body.level, lines=body.lines)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return ScoreResponse(
        id=entry.id,
        score=entry.score,
        level=entry.level,
        lines=entry.lines,
        created_at=entry.created_at,
        username=user.username,
    )


@router.get("/leaderboard", response_model=List[ScoreResponse])
def leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    rows = (
        db.query(Score, User)
        .join(User)
        .order_by(Score.score.desc())
        .limit(limit)
        .all()
    )
    return [
        ScoreResponse(
            id=s.id,
            score=s.score,
            level=s.level,
            lines=s.lines,
            created_at=s.created_at,
            username=u.username,
        )
        for s, u in rows
    ]


@router.get("/rank")
def get_rank(score: int, db: Session = Depends(get_db)):
    """해당 점수의 전체 순위와 총 플레이 수 반환"""
    rank = db.query(Score).filter(Score.score > score).count() + 1
    total = db.query(Score).count()
    return {"rank": rank, "total": total}


@router.get("/me", response_model=List[ScoreResponse])
def my_scores(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entries = (
        db.query(Score)
        .filter(Score.user_id == user.id)
        .order_by(Score.score.desc())
        .limit(10)
        .all()
    )
    return [
        ScoreResponse(
            id=e.id,
            score=e.score,
            level=e.level,
            lines=e.lines,
            created_at=e.created_at,
            username=user.username,
        )
        for e in entries
    ]
