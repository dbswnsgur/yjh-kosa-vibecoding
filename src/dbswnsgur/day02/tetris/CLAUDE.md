# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 작업 규칙

**모든 작업이 완료되기 전에 반드시 테스트를 실행해야 한다.**

```bash
python3 -m pytest backend/tests/ -v
```

테스트가 하나라도 실패하면 작업을 완료로 간주하지 않고, 실패 원인을 수정한 뒤 다시 전체 테스트를 통과시켜야 한다.

## 실행 방법

### Docker Compose (권장)

```bash
# tetris/ 디렉터리에서 실행
docker compose up --build
```

앱과 MySQL 컨테이너가 함께 시작된다. MySQL 헬스체크가 통과된 뒤 앱이 시작된다.

### 로컬 실행 (DB만 Docker)

```bash
# MySQL만 Docker로 실행
docker compose up db -d

# 환경변수 파일 생성
cp .env.example .env

# 패키지 설치
pip3 install -r backend/requirements.txt

# 개발 서버 시작
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
├── docker-compose.yml  # MySQL + app 컨테이너 정의
├── Dockerfile          # FastAPI 앱 이미지
├── .dockerignore       # Docker 빌드 제외 파일 목록 (__pycache__, .env, .git 등)
├── .env.example        # 환경변수 템플릿 (cp .env.example .env)
├── backend/            # FastAPI 백엔드 (Python 패키지)
│   ├── main.py         # 앱 진입점, 라우터 등록, /api/* → 정적파일 마운트 순서
│   ├── models.py       # SQLAlchemy ORM (User, Score, RefreshToken)
│   ├── schemas.py      # Pydantic 요청/응답 스키마
│   ├── auth.py         # JWT 생성/검증, bcrypt 해싱
│   ├── database.py     # DB 엔진(환경변수 기반), get_db 의존성
│   ├── routers/
│   │   ├── auth.py     # /api/auth/* 엔드포인트
│   │   └── scores.py   # /api/scores/* 엔드포인트
│   └── tests/
│       ├── conftest.py          # pytest 픽스처 (인메모리 SQLite, TestClient)
│       ├── test_auth_utils.py   # auth.py 순수 함수 단위 테스트
│       ├── test_auth_api.py     # /api/auth/* 엔드포인트 테스트
│       └── test_scores_api.py   # /api/scores/* 엔드포인트 테스트
├── index.html          # 랜딩 + 로그인/회원가입 + 리더보드
├── game.html           # 게임 화면 (로그인 미인증 시 / 로 리다이렉트)
├── auth.js             # 전역 Auth 객체 (토큰 관리, fetchWithAuth)
├── tetris.js           # 게임 로직 + 점수 저장 연동
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

MySQL 8.0 (Docker Compose로 실행). 연결 정보는 `DATABASE_URL` 환경변수로 주입된다.

- 스키마는 서버 시작 시 `Base.metadata.create_all()`로 자동 생성된다.
- 마이그레이션 도구는 없으며, 스키마 변경 시 컨테이너 볼륨 삭제 후 재시작하면 된다:
  ```bash
  docker compose down -v && docker compose up --build
  ```
- `TESTING=1` 환경변수가 설정된 경우 `create_all`을 건너뛴다 (테스트 환경 격리).
- 단위 테스트는 인메모리 SQLite를 사용하므로 MySQL 없이도 실행 가능하다.

## 테스트

```bash
# tetris/ 디렉터리에서 실행 (Docker 데몬이 실행 중이어야 함)
python3 -m pytest backend/tests/ -v

# 특정 파일만 실행
python3 -m pytest backend/tests/test_auth_utils.py -v
python3 -m pytest backend/tests/test_auth_api.py -v
python3 -m pytest backend/tests/test_scores_api.py -v
```

- **testcontainers + MySQL 8.0** 사용 — 실제 MySQL 컨테이너를 띄워 테스트 실행 (Docker 필수)
- 컨테이너는 세션당 1회 기동(약 15~30초), 테이블은 각 테스트마다 생성/삭제해 격리 보장
- `conftest.py` 첫 줄에서 `TESTING=1`을 설정해 `main.py`의 프로덕션 DB 연결 시도를 차단
- `testcontainers` 4.x는 `mysql://` URL을 반환하므로 `mysql+pymysql://`로 치환해 pymysql 드라이버를 강제
- 총 43개 테스트: 순수 함수 11개 + 인증 API 16개 + 점수 API 16개

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./tetris.db` | DB 연결 문자열. MySQL: `mysql+pymysql://user:pass@host:3306/db?charset=utf8mb4` |
| `SECRET_KEY` | `tetris-dev-secret-key-change-in-production` | JWT 서명 키 (운영 시 반드시 변경) |
| `TESTING` | (미설정) | `1`로 설정 시 서버 시작 시 `create_all` 건너뜀 (pytest에서 자동 설정) |

## 알려진 이슈 및 주의사항

- **bcrypt 버전 고정**: `passlib 1.7.4`는 `bcrypt 4.0+`와 호환되지 않는다. 최신 bcrypt가 72바이트 제한을 엄격하게 적용하면서 passlib 내부의 `detect_wrap_bug` 테스트가 실패해 회원가입/로그인 시 500 에러가 발생한다. `requirements.txt`에 `bcrypt<4.0.0`으로 버전을 고정해 해결한다. passlib을 교체하기 전까지 이 핀을 제거하면 안 된다.
- **RefreshToken.token 컬럼 타입**: MySQL은 `TEXT` 컬럼에 인덱스를 생성할 때 키 길이를 요구한다. `String(512)`로 정의해야 `UNIQUE INDEX`가 정상 생성된다. SQLite는 이 제약이 없어 기존 테스트에서는 드러나지 않았던 MySQL 고유 이슈다.
- **testcontainers URL 드라이버**: `testcontainers` 4.x의 `MySqlContainer.get_connection_url()`은 `mysql://`(MySQLdb 드라이버)를 반환한다. pymysql을 사용하려면 `conftest.py`에서 `mysql+pymysql://`로 치환해야 한다.
