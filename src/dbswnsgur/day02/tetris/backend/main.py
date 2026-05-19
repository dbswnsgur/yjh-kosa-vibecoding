import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine
from .models import Base
from .routers.auth import router as auth_router
from .routers.scores import router as scores_router

if not os.getenv("TESTING"):
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tetris API", docs_url="/api/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(scores_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 프론트엔드 정적 파일 서빙 (backend/ 의 상위 디렉터리)
STATIC_DIR = Path(__file__).parent.parent
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
