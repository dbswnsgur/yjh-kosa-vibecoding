# Tetris 프로젝트 작업 플로우

## 개요

바닐라 JS 테트리스 게임에 FastAPI 백엔드를 붙이고, JWT 인증 + 점수 리더보드 + Docker 배포까지 단계적으로 구축한 기록.

---

## Phase 1 — 프론트엔드 게임 구현 (`fd956ae`)

**목표**: 순수 HTML/CSS/JS로 동작하는 테트리스 게임 완성

### 작업 내용

- `tetris.js`: HTML5 Canvas 기반 게임 로직 전체 구현
  - 7종 테트로미노 정의 및 회전 처리
  - 라인 클리어 + 점수 계산 (1줄=100, 2줄=300, 3줄=500, 4줄=800)
  - 게임 루프 (`requestAnimationFrame`), 레벨별 낙하 속도 증가
  - 키보드 입력 처리 (방향키, 스페이스바 하드드롭)
- `index.html`: 랜딩 페이지 (게임 진입점)
- `game.html`: 게임 화면 (캔버스 + 사이드바)
- `style.css`: 전체 레이아웃 및 UI 스타일링

### 결과

백엔드 없이 로컬에서 완전히 동작하는 테트리스 게임.

---

## Phase 2 — FastAPI 백엔드 + JWT 인증 + 점수 API (`7bb0a5d`)

**목표**: 회원가입/로그인, 점수 저장, 리더보드 API 구축 및 프론트엔드 연동

### 작업 내용

#### 백엔드 구조 설계

```
backend/
├── main.py         # 앱 진입점, 라우터 등록 후 정적 파일 마운트 (순서 중요)
├── models.py       # SQLAlchemy ORM: User, Score, RefreshToken
├── schemas.py      # Pydantic 스키마 (요청/응답 분리)
├── auth.py         # bcrypt 해싱, JWT 생성/검증
├── database.py     # SQLite 엔진, get_db 의존성
└── routers/
    ├── auth.py     # /api/auth/*
    └── scores.py   # /api/scores/*
```

#### 인증 설계 결정사항

| 항목 | 결정 | 이유 |
|------|------|------|
| Access Token 유효기간 | 30분 | 짧게 유지해 탈취 피해 최소화 |
| Refresh Token 유효기간 | 7일 | 자주 로그아웃 없이 사용 가능 |
| Refresh Token 저장 | DB (`refresh_tokens` 테이블) | 서버 측 폐기(rotation/logout) 가능하게 |
| Rotation 방식 | 갱신 시 기존 토큰 `is_revoked=true` | 토큰 재사용 탐지 가능 |

#### 구현된 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/auth/register` | 이메일+닉네임+비밀번호 회원가입 |
| POST | `/api/auth/login` | 로그인 → access/refresh 토큰 반환 |
| POST | `/api/auth/refresh` | refresh_token → 새 토큰 쌍 반환 |
| POST | `/api/auth/logout` | refresh_token 폐기 |
| GET  | `/api/auth/me` | 현재 사용자 정보 (Bearer 인증) |
| POST | `/api/scores` | 게임 점수 저장 |
| GET  | `/api/scores/leaderboard` | 상위 N개 점수 |
| GET  | `/api/scores/rank?score=N` | 해당 점수의 전체 순위 + 총 플레이 수 |
| GET  | `/api/scores/me` | 내 점수 기록 (최대 10개) |

#### 프론트엔드 연동

- `auth.js`: 전역 `Auth` 객체 — 토큰 관리, `fetchWithAuth()` (401 시 자동 refresh 후 재시도, 실패 시 `/` 리다이렉트)
- `tetris.js`: 게임 오버 시 `saveScore()` 1회 호출 (`scoreSubmitted` 플래그로 중복 방지) → 저장 후 순위 조회해 사이드바에 표시
- `index.html`: 로그인/회원가입 폼 + 리더보드 패널

### 결과

로그인한 사용자가 게임 후 자동으로 점수가 저장되고 전체 순위가 표시됨.

---

## Phase 3 — 단위 테스트 + Refresh Token 버그 수정 + 오프라인 모드 (`bfc02cc`)

**목표**: 테스트로 코드 신뢰성 확보, 발견된 버그 수정, 비회원도 게임 가능하도록

### 작업 내용

#### 테스트 작성 (43개)

```
backend/tests/
├── conftest.py           # 인메모리 SQLite(StaticPool) + TestClient + 헬퍼 픽스처
├── test_auth_utils.py    # auth.py 순수 함수 11개
├── test_auth_api.py      # /api/auth/* 16개
└── test_scores_api.py    # /api/scores/* 16개
```

**테스트 격리 전략**: `TESTING=1` 환경변수로 MySQL 연결 차단, `reset_db` 픽스처(autouse)로 각 테스트마다 테이블 생성/삭제.

#### 버그 수정: Refresh Token UNIQUE 충돌

- **원인**: 같은 초에 refresh 요청이 여러 번 오면 `jti` 없이 생성된 JWT가 동일해져 DB UNIQUE 제약 위반
- **수정**: `auth.py`의 `create_refresh_token()`에 `jti` (랜덤 16바이트 hex) 추가 — 같은 초에 생성해도 토큰이 고유하게 보장

#### 오프라인 모드 구현

- `auth.js`에 `Auth.checkBackend()` 추가 (세션 캐싱, 3초 타임아웃으로 백엔드 가용성 확인)
- 백엔드 미연결 시 비회원 모드로 게임 진행 가능 (점수 저장 없이 로컬 플레이)
- `game.html` / `index.html` / `style.css`에 오프라인 상태 UI 반영

#### 작업 규칙 수립 (CLAUDE.md)

모든 작업 완료 전 `python3 -m pytest backend/tests/ -v` 실행 의무화. 테스트 실패 시 완료로 간주하지 않음.

### 결과

43개 테스트 전체 통과. 백엔드 없는 환경에서도 게임 플레이 가능.

---

## Phase 4 — Docker/MySQL 전환 + bcrypt 호환성 버그 수정 (`50bb0eb`)

**목표**: 운영 환경에 가까운 구성으로 전환, 회원가입 500 에러 수정

### 작업 내용

#### 문제: 회원가입 시 500 에러

- **원인**: `passlib 1.7.4`가 `bcrypt 4.0+`와 호환되지 않음. 최신 bcrypt가 72바이트 제한을 엄격하게 적용하면서 passlib 내부 `detect_wrap_bug` 테스트가 ValueError로 실패
- **수정**: `requirements.txt`에 `bcrypt<4.0.0` 핀 추가

#### Docker Compose 구성

```yaml
services:
  db:   # MySQL 8.0, healthcheck 통과 후 app 시작
  app:  # FastAPI, depends_on: db (service_healthy)
```

- `Dockerfile`: Python 3.11-slim 기반 FastAPI 앱 이미지
- `.env.example`: 로컬 개발용 환경변수 템플릿
- MySQL 헬스체크: `mysqladmin ping` (interval 5s, retries 12)

#### MySQL 호환성 수정

| 파일 | 변경 내용 |
|------|-----------|
| `database.py` | `DATABASE_URL` 환경변수 기반으로 전환, MySQL용 `pool_pre_ping`/`pool_recycle` 추가 |
| `models.py` | `String` → `String(255)`, token 컬럼 `String` → `Text` (MySQL 인덱스 길이 제한 대응) |
| `main.py` | `TESTING=1`일 때 `create_all` 스킵 (테스트 격리) |

#### 문서 정비

- `README.md`: Docker Compose 실행법, 알려진 이슈 섹션 추가
- `CLAUDE.md`: 중복 테스트 섹션 제거, 알려진 이슈 및 bcrypt 핀 제거 금지 명시
- `.gitignore`: `.env`, `*.pyc`, `.pytest_cache/` 추가

### 결과

`docker compose up --build` 한 번으로 MySQL + 앱이 함께 기동. 회원가입/로그인 정상 동작. 43개 테스트 전체 통과.

---

## 최종 아키텍처

```
┌─────────────────────────────────────┐
│           Browser                   │
│  index.html / game.html             │
│  auth.js / tetris.js / style.css    │
└────────────┬────────────────────────┘
             │ HTTP (localhost:8000)
┌────────────▼────────────────────────┐
│         FastAPI (uvicorn)           │
│  /api/auth/*   /api/scores/*        │
│  → 정적 파일 마운트 (/)             │
└────────────┬────────────────────────┘
             │ SQLAlchemy (pymysql)
┌────────────▼────────────────────────┐
│         MySQL 8.0                   │
│  users / scores / refresh_tokens    │
└─────────────────────────────────────┘
```

## 교훈 및 주의사항

1. **라우터 등록 순서**: `include_router`는 `app.mount("/")` 보다 반드시 앞에 위치해야 API 라우트가 정적 파일보다 우선 처리됨.
2. **bcrypt 버전 핀**: `passlib 1.7.4`는 `bcrypt 4.0+`와 호환되지 않으므로 `bcrypt<4.0.0`을 유지할 것. passlib을 다른 라이브러리로 교체하기 전까지 이 핀을 제거하면 안 됨.
3. **Refresh Token jti**: 동시 요청 시 UNIQUE 충돌 방지를 위해 반드시 `jti` (랜덤 hex)를 payload에 포함할 것.
4. **테스트 격리**: MySQL 없이도 테스트가 돌아야 CI가 가능함. `TESTING=1` + 인메모리 SQLite 조합을 유지할 것.
