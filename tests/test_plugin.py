import inspect
import json
from types import SimpleNamespace

import pytest
from endstone.event import ActorSpawnEvent, EventPriority

from endstone_antiphantom import AntiPhantom, storage
from endstone_antiphantom.storage import Preferences


def event(location, actor_type="minecraft:phantom", cancelled=False):
    return SimpleNamespace(actor=SimpleNamespace(type=actor_type, location=location), is_cancelled=cancelled)


def command(plugin, sender, *args):
    assert plugin.on_command(sender, SimpleNamespace(name="phantom"), list(args)) is True


def test_real_event_registration_and_no_future_annotation(setup_plugin):
    plugin = setup_plugin.plugin
    annotation = inspect.signature(plugin.on_actor_spawn).parameters["event"].annotation
    assert annotation is ActorSpawnEvent
    assert len(plugin.registered) == 1
    name, callback, priority, owner, ignore_cancelled = plugin.registered[0]
    assert name == "ActorSpawnEvent"
    assert callback == plugin.on_actor_spawn
    assert priority == EventPriority.NORMAL
    assert owner is plugin
    assert ignore_cancelled is True


def test_default_allow_then_toggle_and_status(setup_plugin):
    f = setup_plugin
    p = f.player()
    f.plugin.server.online_players = [p]
    spawn = event(p.location)
    f.plugin.on_actor_spawn(spawn)
    assert not spawn.is_cancelled
    command(f.plugin, p)
    assert "开启（允许生成）" in p.messages[0]
    assert "不限制生成" in p.messages[1]
    p.messages.clear()
    command(f.plugin, p, "off")
    assert p.messages[0] == "已保存：你的幻翼生成偏好为关闭（请求禁止生成）。"
    assert "禁止生成" in p.messages[2]
    spawn = event(p.location)
    f.plugin.on_actor_spawn(spawn)
    assert spawn.is_cancelled
    command(f.plugin, p, "on")
    spawn = event(p.location)
    f.plugin.on_actor_spawn(spawn)
    assert not spawn.is_cancelled


@pytest.mark.parametrize("distance", range(4, 13))
def test_status_event_parity_at_every_distance(setup_plugin, distance):
    f = setup_plugin
    f.plugin._distance = distance
    owner = f.player(x=-0.01, z=-16.01)
    neighbor = f.player("乙", "abcdefab-cdef-abcd-efab-cdefabcdefab", x=16*(distance-1), z=-16)
    f.plugin.server.online_players = [owner, neighbor]
    f.plugin._preferences.set_enabled(owner.unique_id, False)
    for allow_neighbor in [True, False]:
        f.plugin._preferences.set_enabled(neighbor.unique_id, allow_neighbor)
        owner.messages.clear()
        command(f.plugin, owner, "status")
        spawn = event(owner.location)
        f.plugin.on_actor_spawn(spawn)
        assert spawn.is_cancelled is (not allow_neighbor)
        assert ("不限制生成" in owner.messages[1]) is allow_neighbor
        assert ("均已关闭" in owner.messages[1]) is (not allow_neighbor)
        assert ("乙" in owner.messages[1]) is allow_neighbor
        assert "关闭（请求禁止生成）" in owner.messages[0]
        assert "不读取该规则的当前值" in owner.messages[2]


def test_movement_disconnect_and_dimension_are_current(setup_plugin):
    f = setup_plugin
    owner = f.player()
    other = f.player("乙", "abcdefab-cdef-abcd-efab-cdefabcdefab", x=64, z=16)
    f.plugin.server.online_players = [owner, other]
    f.plugin._preferences.set_enabled(owner.unique_id, False)
    def blocked():
        spawn = event(owner.location)
        f.plugin.on_actor_spawn(spawn)
        return spawn.is_cancelled
    assert not blocked()
    other.location = f.location(64, 32)
    assert blocked()
    other.location = f.location(0, 0, "Nether")
    assert blocked()
    other.location = f.location(0, 0)
    assert not blocked()
    f.plugin.server.online_players = [owner]
    assert blocked()
    f.plugin.server.online_players = []
    assert not blocked()


def test_no_cover_status_and_nonphantom_precancelled_no_scan(setup_plugin, monkeypatch):
    f = setup_plugin
    p = f.player()
    command(f.plugin, p, "status")
    assert "没有玩家" in p.messages[1]
    def unexpected(*args):
        pytest.fail("Irrelevant or already cancelled event must not scan players")
    monkeypatch.setattr(f.plugin, "_decision", unexpected)
    zombie = event(p.location, "minecraft:zombie")
    f.plugin.on_actor_spawn(zombie)
    assert not zombie.is_cancelled
    phantom = event(p.location, cancelled=True)
    f.plugin.on_actor_spawn(phantom)
    assert phantom.is_cancelled
    cancelled_zombie = event(p.location, "minecraft:zombie", True)
    f.plugin.on_actor_spawn(cancelled_zombie)
    assert cancelled_zombie.is_cancelled


def test_uuid_survives_rename_and_restart(setup_plugin):
    f = setup_plugin
    original = f.player("OldName")
    command(f.plugin, original, "off")
    renamed = f.player("NewName")
    f.plugin.on_disable()
    f.plugin.on_enable()
    f.plugin.server.online_players = [renamed]
    command(f.plugin, renamed, "status")
    assert "关闭（请求禁止生成）" in renamed.messages[0]
    assert "均已关闭" in renamed.messages[1]
    text = f.plugin._preferences.path.read_text()
    assert "OldName" not in text and "NewName" not in text


def test_acknowledgment_happens_after_save(setup_plugin):
    f = setup_plugin
    p = f.player()
    original_send = p.send_message
    def checked_send(message):
        if message.startswith("已保存"):
            assert not Preferences(f.plugin._preferences.path).enabled(p.unique_id)
        original_send(message)
    p.send_message = checked_send
    command(f.plugin, p, "off")
    assert p.messages[0].startswith("已保存")


def test_save_failure_is_not_acknowledged(setup_plugin, monkeypatch):
    f = setup_plugin
    p = f.player()
    def fail(*args):
        raise OSError("injected disk full")
    monkeypatch.setattr(storage.os, "replace", fail)
    command(f.plugin, p, "off")
    assert p.messages == ["保存失败，你的幻翼设置未更改。请联系管理员查看后台日志。"]
    assert f.plugin._preferences.enabled(p.unique_id)
    assert "Failed to save phantom preference" in f.plugin.logs[-1]


@pytest.mark.parametrize("args", [[], ["status"], ["on"], ["off"], ["unknown"]])
def test_console_has_no_fake_location_or_preference(setup_plugin, args):
    f = setup_plugin
    console = f.sender()
    command(f.plugin, console, *args)
    assert "console has no player identity or current chunk" in console.messages[0]
    assert console.messages[0].isascii()
    assert not f.plugin._preferences.path.exists()


@pytest.mark.parametrize("is_player", [True, False])
def test_permission_denial_does_not_mutate(setup_plugin, is_player):
    f = setup_plugin
    sender = f.player(allowed=False) if is_player else f.sender(False)
    command(f.plugin, sender, "off")
    assert sender.messages == (["你没有使用此命令的权限。"] if is_player else ["Permission denied: antiphantom.command"])
    assert not f.plugin._preferences.path.exists()
    assert AntiPhantom.permissions["antiphantom.command"]["default"] is True
    assert len(AntiPhantom.permissions) == 1


@pytest.mark.parametrize("args", [["unknown"], ["off", "someone"]])
def test_bad_command_is_chinese_and_self_only(setup_plugin, args):
    f = setup_plugin
    p = f.player()
    command(f.plugin, p, *args)
    assert p.messages[0].startswith("用法：")
    assert not f.plugin._preferences.path.exists()


@pytest.mark.parametrize("broken", ["preferences", "properties", "missing_properties"])
def test_failed_initialization_is_disabled_and_guarded(setup_plugin, broken):
    f = setup_plugin
    f.plugin.on_disable()
    properties = f.plugin.data_path.parent.parent / "server.properties"
    if broken == "preferences":
        f.plugin.data_path.mkdir(parents=True)
        target = f.plugin.data_path / "preferences.json"
        target.write_text("{", encoding="utf-8")
    elif broken == "properties":
        target = properties
        target.write_text("tick-distance=nonsense", encoding="utf-8")
    else:
        target = properties
        target.unlink()
    before = target.read_bytes() if target.exists() else None
    f.plugin.on_enable()
    assert f.plugin.disabled == [f.plugin]
    assert f.plugin._preferences is None
    assert len(f.plugin.registered) == 1  # Only the earlier successful enable registered.
    p = f.player()
    command(f.plugin, p, "off")
    assert "不可用" in p.messages[0]
    spawn = event(p.location)
    f.plugin.on_actor_spawn(spawn)
    assert not spawn.is_cancelled
    assert (target.read_bytes() if target.exists() else None) == before
    assert "initialization failed" in f.plugin.logs[-1]


def test_config_clamp_and_missing_key_logged(setup_plugin):
    f = setup_plugin
    properties = f.plugin.data_path.parent.parent / "server.properties"
    properties.write_text("tick-distance=99", encoding="utf-8")
    f.plugin.on_disable()
    f.plugin.on_enable()
    assert f.plugin._distance == 12
    assert any("clamped to 12" in line for line in f.plugin.logs)
    properties.write_text("server-name=Test", encoding="utf-8")
    f.plugin.on_disable()
    f.plugin.on_enable()
    assert f.plugin._distance == 4
    assert any("absent" in line for line in f.plugin.logs)
