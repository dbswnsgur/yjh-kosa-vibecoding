# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 작업 규칙

**모든 작업이 완료되기 전에 반드시 테스트를 실행해야 한다.**

```bash
python3 -m pytest backend/tests/ -v
```

테스트가 하나라도 실패하면 작업을 완료로 간주하지 않고, 실패 원인을 수정한 뒤 다시 전체 테스트를 통과시켜야 한다.

## 실행 방법

```bash
# tetris/ 디렉터리에서 실행
cd src/dbswnsgur/day02/tetris

# 최초 1회 패키지 설치
pip3 install -r backend/requirements.txt

# 개발 서버 시작 (API + 프론트엔드 동시 서빙)
uvicorn backend.main:app --reload --port 8000
```

접속 URL:
- `http://localhost:8000/` — 메인 페이지 (로그인/회원가입)
- `http://localhost:8000/game.html` — 게임 (로그인 필요)
- `http://localhost:8000/api/docs` — Swagger UI

## 아키텍처

FastAPI 백엔드가 API와 프론트엔드 정적 파일을 모두 서빙하는 단일 서버 구조.

```
tetris/
├── backend/          # FastAPI 백엔드 (Python 패키지)
│   ├── main.py       # 앱 진입점, 라우터 등록, /api/* → 정적파일 마운트 순서
│   ├── models.py     # SQLAlchemy ORM (User, Score, RefreshToken)
│   ├── schemas.py    # Pydantic 요청/응답 스키마
│   ├── auth.py       # JWT 생성/검증, bcrypt 해싱
│   ├── database.py   # SQLite 엔진, get_db 의존성
│   ├── routers/
│   │   ├── auth.py   # /api/auth/* 엔드포인트
│   │   └── scores.py # /api/scores/* 엔드포인트
│   └── tests/
│       ├── conftest.py          # pytest 픽스처 (인메모리 DB, TestClient)
│       ├── test_auth_utils.py   # auth.py 순수 함수 단위 테스트
│       ├── test_auth_api.py     # /api/auth/* 엔드포인트 테스트
│       └── test_scores_api.py   # /api/scores/* 엔드포인트 테스트
├── index.html        # 랜딩 + 로그인/회원가입 + 리더보드
├── game.html         # 게임 화면 (로그인 미인증 시 / 로 리다이렉트)
├── auth.js           # 전역 Auth 객체 (토큰 관리, fetchWithAuth)
├── tetris.js         # 게임 로직 + 점수 저장 연동
└── style.css
```

**정적 파일 마운트 순서 주의**: `main.py`에서 `include_router`가 `app.mount("/")`보다 반드시 먼저 등록되어야 API 라우트가 정적 파일보다 우선 처리된다.

## 인증 흐름

- **Access Token**: 30분 유효, JWT payload에 `"type": "access"` 포함
- **Refresh Token**: 7일 유효, DB(`refresh_tokens` 테이블)에 저장, rotation 방식(갱신 시 기존 토큰 `is_revoked=true`). payload에 `"jti"` (랜덤 16바이트 hex) 포함 — 같은 초에 생성해도 토큰이 중복되지 않도록 보장
- **프론트엔드**: `auth.js`의 `Auth.fetchWithAuth()`가 401 응답 시 자동으로 refresh 후 재시도, refresh 실패 시 localStorage 초기화 후 `/`로 리다이렉트
- 토큰 3개 모두 `localStorage`에 저장: `access_token`, `refresh_token`, `username`

## 주요 API 엔드포인트

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| POST | `/api/auth/register` | 불필요 | 이메일+닉네임+비밀번호 회원가입 |
| POST | `/api/auth/login` | 불필요 | 로그인 → 토큰 반환 |
| POST | `/api/auth/refresh` | 불필요 | refresh_token으로 토큰 갱신 |
| POST | `/api/auth/logout` | 불필요 | refresh_token 폐기 |
| GET  | `/api/auth/me` | Bearer | 현재 사용자 정보 |
| POST | `/api/scores` | Bearer | 게임 점수 저장 |
| GET  | `/api/scores/leaderboard` | 불필요 | 상위 N개 점수 (기본 10) |
| GET  | `/api/scores/rank?score=N` | 불필요 | 해당 점수의 전체 순위 + 총 플레이 수 |
| GET  | `/api/scores/me` | Bearer | 내 점수 기록 (최대 10개) |

## 게임 로직과 백엔드 연동 지점

`tetris.js`의 `loop()` 함수에서 `gameOver=true`가 되면 `scoreSubmitted` 플래그로 중복 방지 후 `saveScore()`를 1회 호출한다. `saveScore()`는 점수 저장 후 `/api/scores/rank`로 전체 순위를 조회해 사이드바의 `#score-msg`에 표시한다. 신기록 달성 시 `#best-score` / `#best-user` 패널도 즉시 갱신한다.

## DB

SQLite 파일(`tetris.db`)은 uvicorn 실행 디렉터리(`tetris/`)에 생성된다. 스키마는 서버 시작 시 `Base.metadata.create_all()`로 자동 생성된다. 마이그레이션 도구는 없으며, 스키마 변경 시 `tetris.db` 삭제 후 재시작하면 된다.

## 테스트

```bash
# tetris/ 디렉터리에서 실행
python3 -m pytest backend/tests/ -v

# 특정 파일만 실행
python3 -m pytest backend/tests/test_auth_utils.py -v
python3 -m pytest backend/tests/test_auth_api.py -v
python3 -m pytest backend/tests/test_scores_api.py -v
```

- **인메모리 SQLite + StaticPool** 사용 — 실제 `tetris.db`를 건드리지 않음
- `conftest.py`의 `reset_db` 픽스처(autouse)가 각 테스트 전후로 테이블을 생성/삭제해 완전한 격리 보장
- `get_db` 의존성을 테스트용 세션으로 오버라이드하므로 서버를 실행하지 않아도 됨
- 총 43개 테스트: 순수 함수 11개 + 인증 API 16개 + 점수 API 16개

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SECRET_KEY` | `tetris-dev-secret-key-change-in-production` | JWT 서명 키 (운영 시 반드시 변경) |
