from importlib.metadata import distribution
from pathlib import Path
import inspect

from endstone import Player
from endstone.command import Command
from endstone.event import ActorSpawnEvent
from endstone.level import Level
from endstone.permissions import Permission, PermissionDefault
from endstone.plugin import Plugin

from endstone_antiphantom import AntiPhantom


def test_installed_wheel_discovery_and_api_metadata():
    dist = distribution("endstone-antiphantom")
    assert dist.version == "0.1.0"
    assert set(dist.metadata["Requires-Python"].split(",")) == {">=3.11", "<3.16"}
    assert "site-packages" in str(Path(dist.locate_file("endstone_antiphantom/plugin.py")))
    entries = [e for e in dist.entry_points if e.group == "endstone"]
    assert len(entries) == 1
    assert entries[0].name == "antiphantom"
    assert entries[0].load() is AntiPhantom
    assert issubclass(AntiPhantom, Plugin)
    assert AntiPhantom.api_version == "0.11"
    plugin = AntiPhantom()  # Must not access logger/server/data_folder before host attachment.
    assert plugin._preferences is None
    assert inspect.signature(plugin.on_actor_spawn).parameters["event"].annotation is ActorSpawnEvent


def test_real_sdk_command_and_permission_constructors():
    command = Command("phantom", **AntiPhantom.commands["phantom"])
    assert command.name == "phantom"
    assert command.usages == ["/phantom [action: string]"]
    definition = AntiPhantom.permissions["antiphantom.command"]
    permission = Permission("antiphantom.command", description=definition["description"], default=PermissionDefault.TRUE)
    assert permission.name == "antiphantom.command"
    assert hasattr(Player, "unique_id")
    assert not hasattr(Level, "get_game_rule")
