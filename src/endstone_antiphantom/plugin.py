# Keep real event annotations: Endstone 0.11 register_events does not resolve strings.
from pathlib import Path

from endstone import Player
from endstone.command import Command, CommandSender
from endstone.event import ActorSpawnEvent, event_handler
from endstone.level import Location
from endstone.plugin import Plugin

from .coverage import Chunk, Decision, PlayerCoverage, decide
from .settings import read_tick_distance
from .storage import Preferences


class AntiPhantom(Plugin):
    api_version = "0.11"
    description = "Per-player phantom spawn preferences"
    commands = {
        "phantom": {
            "description": "设置自己的幻翼生成偏好，或查询当前位置的插件限制",
            "usages": ["/phantom [action: string]"],
        }
    }
    permissions = {
        "antiphantom.command": {
            "description": "Use /phantom to manage your own preference and inspect your current chunk",
            "default": True,
        }
    }

    def __init__(self):
        super().__init__()
        self._preferences: Preferences | None = None
        self._distance = 4

    def on_enable(self) -> None:
        self._preferences = None
        path = Path.cwd() / "server.properties"
        try:
            setting = read_tick_distance(path)
            preferences = Preferences(Path(self.data_folder) / "preferences.json")
        except (OSError, ValueError) as error:
            self.logger.error(f"AntiPhantom initialization failed; existing files are unchanged: {error}")
            self.server.plugin_manager.disable_plugin(self)
            return
        self._distance = setting.effective
        self._preferences = preferences
        if setting.configured is None:
            self.logger.info(f"tick-distance is absent in {path}; using the BDS default 4")
        elif setting.configured != setting.effective:
            self.logger.warning(
                f"tick-distance={setting.configured} is clamped to {setting.effective} (BDS range 4..12)"
            )
        self.register_events(self)
        self.logger.info(f"AntiPhantom enabled; tick-distance={self._distance}, default preference=on")
        self.logger.info("Spawn policy only; natural phantoms still require global doinsomnia and vanilla conditions")

    def on_disable(self) -> None:
        self._preferences = None

    @staticmethod
    def _chunk(location: Location) -> Chunk:
        dimension = location.dimension
        return Chunk.at((dimension.level.name, dimension.name), location.x, location.z)

    def _decision(self, chunk: Chunk) -> Decision:
        # Called only by spawn events and status requests; positions are always current.
        preferences = self._preferences
        assert preferences is not None
        players = (
            PlayerCoverage(player.name, self._chunk(player.location), preferences.enabled(player.unique_id))
            for player in self.server.online_players
        )
        return decide(chunk, players, self._distance)

    @event_handler(ignore_cancelled=True)
    def on_actor_spawn(self, event: ActorSpawnEvent) -> None:
        if self._preferences is None or event.is_cancelled or event.actor.type != "minecraft:phantom":
            return
        if self._decision(self._chunk(event.actor.location)).blocked:
            event.is_cancelled = True

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        is_player = isinstance(sender, Player)
        # Check here so plugin-generated permission errors follow the caller's language.
        if not sender.has_permission("antiphantom.command"):
            sender.send_message("你没有使用此命令的权限。" if is_player else "Permission denied: antiphantom.command")
            return True
        if not is_player:
            sender.send_message(
                "Use /phantom [on|off|status] in game. This command changes only the caller's preference; "
                "the console has no player identity or current chunk."
            )
            return True
        if self._preferences is None:
            sender.send_message("幻翼设置当前不可用，请联系管理员查看后台日志。")
            return True
        action = args[0].lower() if args else "status"
        if len(args) > 1 or action not in {"on", "off", "status"}:
            sender.send_message("用法：/phantom on 允许生成；/phantom off 关闭生成；/phantom status 查询当前位置。")
            return True
        if action != "status":
            enabled = action == "on"
            try:
                self._preferences.set_enabled(sender.unique_id, enabled)
            except OSError as error:
                self.logger.error(f"Failed to save phantom preference for UUID {sender.unique_id}: {error}")
                sender.send_message("保存失败，你的幻翼设置未更改。请联系管理员查看后台日志。")
                return True
            sender.send_message("已保存：你的幻翼生成偏好为" + ("开启（允许生成）。" if enabled else "关闭（请求禁止生成）。"))
        self._send_status(sender)
        return True

    def _send_status(self, player: Player) -> None:
        preferences = self._preferences
        assert preferences is not None
        chunk = self._chunk(player.location)
        decision = self._decision(chunk)
        own = "开启（允许生成）" if preferences.enabled(player.unique_id) else "关闭（请求禁止生成）"
        player.send_message(f"你的设置：{own}。")
        if decision.blocked:
            effect = f"禁止生成；覆盖此区块的 {decision.covered_count} 名玩家均已关闭。"
        elif decision.enabled_names:
            effect = "不限制生成；覆盖此区块且已开启的玩家：" + "、".join(decision.enabled_names) + "。"
        else:
            effect = "不限制生成；没有玩家的模拟候选范围覆盖此区块，保留原版行为。"
        player.send_message(f"当前位置（区块 {chunk.x}, {chunk.z}；tick-distance={self._distance}）：{effect}")
        player.send_message("这里只显示本插件的限制；自然生成仍需全局 doinsomnia 开启并满足原版条件，本插件不读取该规则的当前值。")
