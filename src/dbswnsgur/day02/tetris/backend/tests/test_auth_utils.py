from datetime import timedelta

from ..auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plain(self):
        assert hash_password("secret") != "secret"

    def test_verify_correct_password(self):
        hashed = hash_password("secret")
        assert verify_password("secret", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("secret")
        assert verify_password("wrong", hashed) is False

    def test_same_password_different_hashes(self):
        assert hash_password("secret") != hash_password("secret")


class TestAccessToken:
    def test_decode_returns_correct_sub(self):
        token = create_access_token({"sub": "42"})
        payload = decode_token(token)
        assert payload["sub"] == "42"

    def test_decode_type_is_access(self):
        token = create_access_token({"sub": "1"})
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_expired_token_returns_none(self):
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None


class TestRefreshToken:
    def test_decode_returns_correct_sub(self):
        token = create_refresh_token({"sub": "99"})
        payload = decode_token(token)
        assert payload["sub"] == "99"

    def test_decode_type_is_refresh(self):
        token = create_refresh_token({"sub": "1"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"


class TestDecodeToken:
    def test_invalid_token_returns_none(self):
        assert decode_token("this.is.invalid") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token({"sub": "1"})
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_empty_string_returns_none(self):
        assert decode_token("") is None
