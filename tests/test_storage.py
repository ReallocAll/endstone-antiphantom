import json
from pathlib import Path
from uuid import UUID

import pytest

from endstone_antiphantom import storage
from endstone_antiphantom.storage import Preferences

IDENTITY = UUID("12345678-1234-5678-90ab-123456789abc")
OTHER = UUID("abcdefab-cdef-abcd-efab-cdefabcdefab")


def test_default_and_restart(tmp_path):
    path = tmp_path / "preferences.json"
    preferences = Preferences(path)
    assert preferences.enabled(IDENTITY)
    assert not path.exists()
    preferences.set_enabled(IDENTITY, False)
    assert not preferences.enabled(IDENTITY)
    assert not Preferences(path).enabled(IDENTITY)
    assert Preferences(path).enabled(OTHER)
    preferences.set_enabled(IDENTITY, True)
    assert Preferences(path).enabled(IDENTITY)
    data = json.loads(path.read_text())
    assert data == {"version": 1, "players": {str(IDENTITY): True}}
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize("body", [
    "{", "[]", '{}', '{"version":1,"players":{},"extra":1}',
    '{"version":2,"players":{}}', '{"version":true,"players":{}}',
    '{"version":1,"players":[]}', '{"version":1,"players":{"NotAUUID":false}}',
    '{"version":1,"players":{"12345678-1234-5678-90ab-123456789abc":0}}',
    '{"version":1,"players":{"12345678-1234-5678-90ab-123456789abc":"false"}}',
    '{"version":1,"players":{},"players":{}}',
    '{"version":1,"players":{"12345678-1234-5678-90ab-123456789abc":false,"12345678-1234-5678-90ab-123456789abc":true}}',
])
def test_corrupt_file_is_preserved(tmp_path, body):
    path = tmp_path / "preferences.json"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError):
        Preferences(path)
    assert path.read_text(encoding="utf-8") == body


def test_invalid_utf8_preserved(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_bytes(b"\xff")
    with pytest.raises(ValueError):
        Preferences(path)
    assert path.read_bytes() == b"\xff"


@pytest.mark.parametrize("failure_point", ["replace", "fsync", "temporary", "mkdir"])
def test_failed_save_preserves_memory_and_file(tmp_path, monkeypatch, failure_point):
    path = tmp_path / "preferences.json"
    preferences = Preferences(path)
    preferences.set_enabled(IDENTITY, False)
    before = path.read_bytes()
    def fail(*args, **kwargs):
        raise OSError(f"injected {failure_point} failure")
    targets = {
        "replace": (storage.os, "replace"), "fsync": (storage.os, "fsync"),
        "temporary": (storage.tempfile, "NamedTemporaryFile"), "mkdir": (Path, "mkdir"),
    }
    monkeypatch.setattr(*targets[failure_point], fail)
    with pytest.raises(OSError):
        preferences.set_enabled(IDENTITY, True)
    assert not preferences.enabled(IDENTITY)
    assert path.read_bytes() == before
    assert list(tmp_path.glob("*.tmp")) == []


def test_commit_order(tmp_path, monkeypatch):
    path = tmp_path / "preferences.json"
    preferences = Preferences(path)
    real_replace = storage.os.replace
    def checked_replace(source, destination):
        assert preferences.enabled(IDENTITY) is True
        assert json.loads(Path(source).read_text())["players"][str(IDENTITY)] is False
        assert Path(source).parent == destination.parent
        real_replace(source, destination)
    monkeypatch.setattr(storage.os, "replace", checked_replace)
    preferences.set_enabled(IDENTITY, False)
    assert not preferences.enabled(IDENTITY)
