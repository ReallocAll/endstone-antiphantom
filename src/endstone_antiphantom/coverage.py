"""Pure, event-time coverage policy; no loaded-chunk or movement cache."""

from dataclasses import dataclass
from math import floor
from collections.abc import Iterable


@dataclass(frozen=True)
class Chunk:
    # Level name is unique in the public API; dimension name distinguishes custom dimensions.
    dimension: tuple[str, str]
    x: int
    z: int

    @classmethod
    def at(cls, dimension: tuple[str, str], x: float, z: float) -> "Chunk":
        return cls(dimension, floor(x / 16), floor(z / 16))


@dataclass(frozen=True)
class PlayerCoverage:
    name: str
    chunk: Chunk
    enabled: bool


@dataclass(frozen=True)
class Decision:
    covered_count: int
    enabled_names: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return self.covered_count > 0 and not self.enabled_names


def covers(center: Chunk, target: Chunk, distance: int) -> bool:
    """BDS 1.26.52.3 candidate footprint, from the supplied binary investigation."""
    if center.dimension != target.dimension:
        return False
    dx, dz = abs(center.x - target.x), abs(center.z - target.z)
    return max(dx, dz) <= distance and dx + dz <= distance + 1


def decide(target: Chunk, players: Iterable[PlayerCoverage], distance: int) -> Decision:
    """Any covered enabled player wins; an uncovered chunk is left unchanged."""
    count = 0
    enabled = []
    for player in players:
        if covers(player.chunk, target, distance):
            count += 1
            if player.enabled:
                enabled.append(player.name)
    return Decision(count, tuple(enabled))
