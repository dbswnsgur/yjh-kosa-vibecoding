import os
os.environ["TESTING"] = "1"  # main.py의 create_all이 프로덕션 DB에 연결 시도하지 않도록

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.mysql import MySqlContainer

from ..database import Base, get_db
from ..main import app


@pytest.fixture(scope="session")
def mysql_container():
    with MySqlContainer("mysql:8.0") as mysql:
        yield mysql


@pytest.fixture(scope="session")
def db_engine(mysql_container):
    # testcontainers 4.x returns mysql:// (MySQLdb); force pymysql driver
    url = mysql_container.get_connection_url().replace("mysql://", "mysql+pymysql://", 1)
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_db(db_engine):
    Base.metadata.create_all(bind=db_engine)
    yield
    Base.metadata.drop_all(bind=db_engine)


@pytest.fixture
def db(db_engine):
    session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123",
    })
    return {"email": "test@example.com", "username": "testuser", "password": "password123"}


@pytest.fixture
def auth_headers(client, registered_user):
    res = client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    data = res.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "refresh_token": data["refresh_token"],
        "user_id": data["user_id"],
    }
