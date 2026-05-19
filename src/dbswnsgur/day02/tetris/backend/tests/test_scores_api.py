def _save_score(client, headers, score=1000, level=3, lines=10):
    return client.post("/api/scores", json={"score": score, "level": level, "lines": lines},
                       headers=headers)


class TestSaveScore:
    def test_success(self, client, auth_headers):
        res = _save_score(client, auth_headers["headers"])
        assert res.status_code == 201
        data = res.json()
        assert data["score"] == 1000
        assert data["level"] == 3
        assert data["lines"] == 10
        assert "id" in data

    def test_unauthorized(self, client):
        res = _save_score(client, {})
        assert res.status_code == 401

    def test_invalid_token(self, client):
        res = _save_score(client, {"Authorization": "Bearer bad.token"})
        assert res.status_code == 401


class TestLeaderboard:
    def test_empty(self, client):
        res = client.get("/api/scores/leaderboard")
        assert res.status_code == 200
        assert res.json() == []

    def test_sorted_by_score_desc(self, client, auth_headers):
        for score in [300, 1000, 500]:
            _save_score(client, auth_headers["headers"], score=score)

        res = client.get("/api/scores/leaderboard")
        assert res.status_code == 200
        scores = [entry["score"] for entry in res.json()]
        assert scores == sorted(scores, reverse=True)

    def test_limit_param(self, client, auth_headers):
        for score in [100, 200, 300, 400, 500]:
            _save_score(client, auth_headers["headers"], score=score)

        res = client.get("/api/scores/leaderboard?limit=3")
        assert res.status_code == 200
        assert len(res.json()) == 3

    def test_default_limit_is_10(self, client, auth_headers):
        for i in range(15):
            _save_score(client, auth_headers["headers"], score=i * 100)

        res = client.get("/api/scores/leaderboard")
        assert len(res.json()) <= 10


class TestRank:
    def test_rank_1_when_highest(self, client, auth_headers):
        _save_score(client, auth_headers["headers"], score=500)
        res = client.get("/api/scores/rank?score=600")
        assert res.status_code == 200
        assert res.json()["rank"] == 1

    def test_rank_last_when_lowest(self, client, auth_headers):
        for score in [300, 500, 700]:
            _save_score(client, auth_headers["headers"], score=score)

        res = client.get("/api/scores/rank?score=100")
        data = res.json()
        assert data["rank"] == 4

    def test_total_count(self, client, auth_headers):
        for score in [100, 200, 300]:
            _save_score(client, auth_headers["headers"], score=score)

        res = client.get("/api/scores/rank?score=150")
        data = res.json()
        assert data["total"] == 3

    def test_no_scores(self, client):
        res = client.get("/api/scores/rank?score=500")
        assert res.status_code == 200
        data = res.json()
        assert data["rank"] == 1
        assert data["total"] == 0


class TestMyScores:
    def test_success(self, client, auth_headers):
        _save_score(client, auth_headers["headers"], score=999)
        res = client.get("/api/scores/me", headers=auth_headers["headers"])
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["score"] == 999

    def test_sorted_by_score_desc(self, client, auth_headers):
        for score in [200, 800, 500]:
            _save_score(client, auth_headers["headers"], score=score)

        res = client.get("/api/scores/me", headers=auth_headers["headers"])
        scores = [entry["score"] for entry in res.json()]
        assert scores == sorted(scores, reverse=True)

    def test_max_10_results(self, client, auth_headers):
        for i in range(15):
            _save_score(client, auth_headers["headers"], score=i * 100)

        res = client.get("/api/scores/me", headers=auth_headers["headers"])
        assert len(res.json()) <= 10

    def test_unauthorized(self, client):
        res = client.get("/api/scores/me")
        assert res.status_code == 401

    def test_only_own_scores(self, client, auth_headers):
        # 두 번째 유저 생성 후 점수 저장
        client.post("/api/auth/register", json={
            "email": "other@example.com",
            "username": "otheruser",
            "password": "pass1234",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "other@example.com",
            "password": "pass1234",
        })
        other_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
        _save_score(client, other_headers, score=9999)

        _save_score(client, auth_headers["headers"], score=1000)

        res = client.get("/api/scores/me", headers=auth_headers["headers"])
        assert all(entry["score"] != 9999 for entry in res.json())
