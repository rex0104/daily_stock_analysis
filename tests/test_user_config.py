"""Tests for per-user config storage (UserConfigManager)."""

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.storage import Base, User
from src.migration import ensure_schema_current
from src.core.user_config_manager import UserConfigManager


@pytest.fixture
def db(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_schema_current(engine)
    sf = sessionmaker(bind=engine)
    # Create a test user
    with sf() as s:
        s.add(User(
            id="user1",
            email="test@test.com",
            nickname="test",
            password_hash="h",
            password_salt="s",
        ))
        s.commit()
    return sf


def test_empty_user_settings_returns_env_example_defaults(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("FOO=bar\nBAZ=qux\n")
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    config = mgr.read_config_map()
    assert config["FOO"] == "bar"
    assert config["BAZ"] == "qux"


def test_user_settings_override_defaults(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("FOO=default\n")
    # Set user settings directly in DB
    with db() as s:
        user = s.query(User).filter_by(id="user1").first()
        user.settings = json.dumps({"FOO": "custom"})
        s.commit()
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    config = mgr.read_config_map()
    assert config["FOO"] == "custom"


def test_apply_updates(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    updated, skipped, version = mgr.apply_updates(
        [("KEY1", "val1"), ("KEY2", "val2")], set(), "******"
    )
    assert set(updated) == {"KEY1", "KEY2"}
    assert skipped == []
    # Verify persisted
    config = mgr.read_config_map()
    assert config["KEY1"] == "val1"
    assert config["KEY2"] == "val2"


def test_apply_updates_skips_masked_sensitive(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    # First set a real value
    mgr.apply_updates([("SECRET", "real_value")], set(), "******")
    # Then update with mask token
    updated, skipped, _ = mgr.apply_updates(
        [("SECRET", "******")], {"SECRET"}, "******"
    )
    assert "SECRET" in skipped
    assert "SECRET" not in updated
    assert mgr.read_config_map()["SECRET"] == "real_value"


def test_apply_updates_skips_unchanged(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    mgr.apply_updates([("K", "v")], set(), "******")
    # Same value again
    updated, skipped, _ = mgr.apply_updates([("K", "v")], set(), "******")
    assert updated == []
    assert skipped == []


def test_config_version_changes_on_update(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    v1 = mgr.get_config_version()
    mgr.apply_updates([("X", "1")], set(), "******")
    v2 = mgr.get_config_version()
    assert v1 != v2
    assert v2.startswith("user:")


def test_get_updated_at_returns_none(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    assert mgr.get_updated_at() is None


def test_missing_env_example(db, tmp_path):
    env_example = tmp_path / "nonexistent" / ".env.example"
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    config = mgr.read_config_map()
    assert config == {}


def test_nonexistent_user_returns_empty(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("A=1\n")
    mgr = UserConfigManager(db, "no_such_user", env_example_path=env_example)
    config = mgr.read_config_map()
    # Still get defaults, just no user overrides
    assert config["A"] == "1"


def test_corrupt_settings_json_returns_empty(db, tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("X=default\n")
    # Write invalid JSON to settings
    with db() as s:
        user = s.query(User).filter_by(id="user1").first()
        user.settings = "not valid json {"
        s.commit()
    mgr = UserConfigManager(db, "user1", env_example_path=env_example)
    config = mgr.read_config_map()
    # Falls back to defaults only
    assert config["X"] == "default"
