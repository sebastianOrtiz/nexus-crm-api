"""
Unit tests for security utilities (password hashing and JWT).

These tests do not require a database and run very fast.
"""

from uuid import uuid4

import pytest

from src.core.enums import TokenType, UserRole
from src.core.exceptions import UnauthorizedError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for bcrypt hash/verify utilities."""

    def test_hash_is_not_plain_text(self) -> None:
        """The hash must not equal the plain-text input."""
        plain = "MySecret1"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_verify_correct_password(self) -> None:
        """Correct plain-text verifies against its hash."""
        plain = "AnotherSecret99"
        assert verify_password(plain, hash_password(plain)) is True

    def test_verify_wrong_password(self) -> None:
        """Incorrect plain-text does not verify."""
        assert verify_password("wrong", hash_password("correct")) is False

    def test_two_hashes_differ(self) -> None:
        """bcrypt salting means the same input produces different hashes."""
        plain = "SamePassword1"
        assert hash_password(plain) != hash_password(plain)


class TestJWT:
    """Tests for JWT creation and decoding."""

    def test_access_token_payload(self) -> None:
        """Access token payload contains expected keys."""
        user_id = uuid4()
        org_id = uuid4()
        token = create_access_token(user_id, org_id, UserRole.OWNER.value)
        payload = decode_access_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["org"] == str(org_id)
        assert payload["role"] == UserRole.OWNER.value
        assert payload["type"] == TokenType.ACCESS.value

    def test_refresh_token_payload(self) -> None:
        """Refresh token payload contains expected keys and no role."""
        user_id = uuid4()
        org_id = uuid4()
        token = create_refresh_token(user_id, org_id)
        payload = decode_refresh_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["org"] == str(org_id)
        assert payload["type"] == TokenType.REFRESH.value
        assert "role" not in payload

    def test_decode_access_token_rejects_refresh_token(self) -> None:
        """``decode_access_token`` raises when given a refresh token."""
        token = create_refresh_token(uuid4(), uuid4())
        with pytest.raises(UnauthorizedError):
            decode_access_token(token)

    def test_decode_refresh_token_rejects_access_token(self) -> None:
        """``decode_refresh_token`` raises when given an access token."""
        token = create_access_token(uuid4(), uuid4(), UserRole.ADMIN.value)
        with pytest.raises(UnauthorizedError):
            decode_refresh_token(token)

    def test_invalid_token_raises_unauthorized(self) -> None:
        """Garbage string raises ``UnauthorizedError``."""
        with pytest.raises(UnauthorizedError):
            decode_token("this.is.not.a.jwt")

    def test_tampered_signature_raises_unauthorized(self) -> None:
        """Modifying the signature part raises ``UnauthorizedError``."""
        token = create_access_token(uuid4(), uuid4(), UserRole.OWNER.value)
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsignature"
        with pytest.raises(UnauthorizedError):
            decode_token(tampered)
