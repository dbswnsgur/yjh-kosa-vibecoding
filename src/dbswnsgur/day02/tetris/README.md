# Tetris

FastAPI 백엔드 + 바닐라 JS 프론트엔드로 구현한 테트리스 게임. JWT 인증, 점수 저장, 리더보드 기능을 포함한다.

## 실행

```bash
# 최초 1회 패키지 설치
pip3 install -r backend/requirements.txt

# 개발 서버 시작
uvicorn backend.main:app --reload --port 8000
```

| URL | 설명 |
|-----|------|
| `http://localhost:8000/` | 메인 페이지 (로그인/회원가입) |
| `http://localhost:8000/game.html` | 게임 화면 (로그인 필요) |
| `http://localhost:8000/api/docs` | Swagger UI |

## 테스트

### 실행 방법

```bash
# 전체 테스트
python3 -m pytest backend/tests/ -v

# 파일별 실행
python3 -m pytest backend/tests/test_auth_utils.py -v   # 순수 함수
python3 -m pytest backend/tests/test_auth_api.py -v     # 인증 API
python3 -m pytest backend/tests/test_scores_api.py -v   # 점수 API
```

### 구조

```
backend/tests/
├── conftest.py           # 공통 픽스처 (인메모리 DB, TestClient, 유저/토큰 헬퍼)
├── test_auth_utils.py    # auth.py 순수 함수 단위 테스트 (11개)
├── test_auth_api.py      # /api/auth/* 엔드포인트 테스트 (16개)
└── test_scores_api.py    # /api/scores/* 엔드포인트 테스트 (16개)
```

### 테스트 설계

- **DB 격리**: `sqlite:///:memory:` + `StaticPool`으로 실제 `tetris.db`를 건드리지 않음. 각 테스트는 `reset_db` 픽스처(autouse)가 테이블을 생성/삭제해 완전히 격리됨.
- **의존성 주입 오버라이드**: `get_db`를 테스트용 세션으로 교체하므로 서버를 띄울 필요 없음.
- **총 43개** 테스트.

### 커버 범위

| 파일 | 테스트 항목 |
|------|------------|
| `test_auth_utils.py` | 비밀번호 해싱/검증, access/refresh 토큰 생성 및 디코딩, 만료·변조 토큰 처리 |
| `test_auth_api.py` | 회원가입(정상/중복/유효성), 로그인(정상/오답/없는 계정), refresh rotation, 로그아웃, `/me` 인증 |
| `test_scores_api.py` | 점수 저장, 리더보드 정렬·limit, 순위 계산, 내 점수 조회, 유저 격리 |

## 기술 스택

- **백엔드**: FastAPI, SQLAlchemy, SQLite, python-jose, passlib
- **프론트엔드**: 바닐라 JS, HTML5 Canvas
- **테스트**: pytest, httpx
