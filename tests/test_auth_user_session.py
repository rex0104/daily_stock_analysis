# tests/test_auth_user_session.py
import tempfile
from pathlib import Path
from unittest.mock import patch

import src.auth as auth


def _reset_auth_globals() -> None:
    auth._auth_enabled = None
    auth._session_secret = None


def _make_patch_ctx(temp_dir: Path):
    """Return a context manager that enables auth and redirects data dir."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        auth._auth_enabled = True
        with patch.object(auth, "_is_auth_enabled_from_env", return_value=True), \
             patch.object(auth, "_get_data_dir", return_value=temp_dir):
            yield

    return _ctx()


def test_create_and_verify_user_session():
    from src.auth import create_user_session, verify_session_user
    _reset_auth_globals()
    with tempfile.TemporaryDirectory() as tmp:
        with _make_patch_ctx(Path(tmp)):
            user_id = "abc123def456"
            token = create_user_session(user_id)
            assert token
            parts = token.split(".")
            assert len(parts) == 4  # user_id.nonce.ts.sig
            assert parts[0] == user_id
            result = verify_session_user(token)
            assert result == user_id


def test_verify_session_user_invalid_token():
    from src.auth import verify_session_user
    _reset_auth_globals()
    with tempfile.TemporaryDirectory() as tmp:
        with _make_patch_ctx(Path(tmp)):
            assert verify_session_user("garbage") is None
            assert verify_session_user("") is None
            assert verify_session_user(None) is None


def test_verify_session_user_tampered_signature():
    from src.auth import create_user_session, verify_session_user
    _reset_auth_globals()
    with tempfile.TemporaryDirectory() as tmp:
        with _make_patch_ctx(Path(tmp)):
            token = create_user_session("user1")
            parts = token.split(".")
            parts[3] = "0" * len(parts[3])  # tamper signature
            assert verify_session_user(".".join(parts)) is None


def test_verify_session_user_tampered_user_id():
    from src.auth import create_user_session, verify_session_user
    _reset_auth_globals()
    with tempfile.TemporaryDirectory() as tmp:
        with _make_patch_ctx(Path(tmp)):
            token = create_user_session("user1")
            parts = token.split(".")
            parts[0] = "hacker"
            assert verify_session_user(".".join(parts)) is None
