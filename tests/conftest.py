from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from endstone.plugin import Plugin

from endstone_antiphantom import plugin as module
from endstone_antiphantom import AntiPhantom


class Sender:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.messages = []

    def has_permission(self, permission):
        assert permission == "antiphantom.command"
        return self.allowed

    def send_message(self, message):
        self.messages.append(message)


class Player(Sender):
    def __init__(self, name="甲", identity="12345678-1234-5678-90ab-123456789abc", x=0, z=0, dimension="Overworld", level="world", allowed=True):
        super().__init__(allowed)
        self.name = name
        self.unique_id = UUID(identity)
        self.location = location(x, z, dimension, level)


def location(x=0, z=0, dimension="Overworld", level="world"):
    return SimpleNamespace(x=x, z=z, dimension=SimpleNamespace(name=dimension, level=SimpleNamespace(name=level)))


class Harness(AntiPhantom):
    def __init__(self, data_path):
        super().__init__()
        self.data_path = data_path
        self.registered = []
        self.disabled = []
        self.logs = []
        self.fake_server = SimpleNamespace(
            online_players=[],
            plugin_manager=SimpleNamespace(
                disable_plugin=lambda plugin: self.disabled.append(plugin),
                register_event=lambda *args: self.registered.append(args),
            ),
        )

    @property
    def data_folder(self):
        return self.data_path

    @property
    def server(self):
        return self.fake_server

    @property
    def logger(self):
        return SimpleNamespace(**{level: lambda message: self.logs.append(message) for level in ("info", "warning", "error")})

    @property
    def name(self):
        return "antiphantom"

    @property
    def is_enabled(self):
        return True

    def register_events(self, listener):
        # Exercise the real 0.11.14 inspector with the real bound event method,
        # without reading uninitialized C++ host properties on this test harness.
        Plugin.register_events(self, SimpleNamespace(on_actor_spawn=listener.on_actor_spawn))


@pytest.fixture
def setup_plugin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "server.properties").write_text("tick-distance=4\n", encoding="utf-8")
    monkeypatch.setattr(module, "Player", Player)
    harness = Harness(tmp_path / "plugins" / "antiphantom")
    harness.on_enable()
    assert not harness.disabled
    return SimpleNamespace(plugin=harness, player=Player, sender=Sender, location=location)
