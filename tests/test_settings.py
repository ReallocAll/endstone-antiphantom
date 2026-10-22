from pathlib import Path

import pytest

from endstone_antiphantom.settings import TickDistance, read_tick_distance


@pytest.mark.parametrize("configured,effective", [(-1, 4), (0, 4), (3, 4), *[(n, n) for n in range(4, 13)], (13, 12), (999, 12)])
def test_distance_and_clamp(tmp_path, configured, effective):
    path = tmp_path / "server.properties"
    path.write_text(f"# comment\nserver-name=Test\n tick-distance = {configured} \n", encoding="utf-8")
    assert read_tick_distance(path) == TickDistance(configured, effective)


def test_missing_key_is_the_only_default(tmp_path):
    path = tmp_path / "server.properties"
    path.write_text("# tick-distance=12\nserver-name=Test\n", encoding="utf-8")
    assert read_tick_distance(path) == TickDistance(None, 4)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        read_tick_distance(path)


@pytest.mark.parametrize("body", [
    "tick-distance=", "tick-distance=true", "tick-distance=4.0", "tick-distance=4 # note",
    "tick-distance=0x8", "tick-distance=４", "tick-distance", "tick-distance: 4", "tick-distance 4",
    "tick-distance=4\ntick-distance=5",
])
def test_invalid_values_and_duplicate_key(tmp_path, body):
    path = tmp_path / "server.properties"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError):
        read_tick_distance(path)
    assert path.read_text(encoding="utf-8") == body


def test_unreadable_file_is_not_a_default(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("denied")
    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(PermissionError):
        read_tick_distance(tmp_path / "server.properties")
