class TestRegister:
    def test_success(self, client):
        res = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "pass1234",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "new@example.com"
        assert data["username"] == "newuser"
        assert "id" in data

    def test_duplicate_email(self, client, registered_user):
        res = client.post("/api/auth/register", json={
            "email": registered_user["email"],
            "username": "other",
            "password": "pass1234",
        })
        assert res.status_code == 400

    def test_invalid_email_format(self, client):
        res = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "username": "user",
            "password": "pass1234",
        })
        assert res.status_code == 422


class TestLogin:
    def test_success(self, client, registered_user):
        res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["username"] == registered_user["username"]

    def test_wrong_password(self, client, registered_user):
        res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": "wrongpassword",
        })
        assert res.status_code == 401

    def test_unknown_email(self, client):
        res = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "pass1234",
        })
        assert res.status_code == 401


class TestRefresh:
    def test_success_returns_new_tokens(self, client, auth_headers):
        res = client.post("/api/auth/refresh", json={
            "refresh_token": auth_headers["refresh_token"],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["refresh_token"] != auth_headers["refresh_token"]
        assert "access_token" in data

    def test_rotation_revokes_old_token(self, client, auth_headers):
        client.post("/api/auth/refresh", json={
            "refresh_token": auth_headers["refresh_token"],
        })
        res = client.post("/api/auth/refresh", json={
            "refresh_token": auth_headers["refresh_token"],
        })
        assert res.status_code == 401

    def test_invalid_token(self, client):
        res = client.post("/api/auth/refresh", json={
            "refresh_token": "invalid.token.value",
        })
        assert res.status_code == 401


class TestLogout:
    def test_success(self, client, auth_headers):
        res = client.post("/api/auth/logout", json={
            "refresh_token": auth_headers["refresh_token"],
        })
        assert res.status_code == 200

    def test_token_unusable_after_logout(self, client, auth_headers):
        client.post("/api/auth/logout", json={
            "refresh_token": auth_headers["refresh_token"],
        })
        res = client.post("/api/auth/refresh", json={
            "refresh_token": auth_headers["refresh_token"],
        })
        assert res.status_code == 401


class TestMe:
    def test_success(self, client, registered_user, auth_headers):
        res = client.get("/api/auth/me", headers=auth_headers["headers"])
        assert res.status_code == 200
        assert res.json()["email"] == registered_user["email"]

    def test_no_token(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_invalid_token(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token"})
        assert res.status_code == 401

    def test_access_token_required_not_refresh(self, client, auth_headers):
        res = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {auth_headers['refresh_token']}"
        })
        assert res.status_code == 401
