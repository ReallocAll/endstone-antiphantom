"""Read only the server's tick-distance; never rewrite server.properties."""

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class TickDistance:
    configured: int | None
    effective: int


def read_tick_distance(path: Path) -> TickDistance:
    """Absent key defaults to 4; unreadable files and ambiguous keys are errors."""
    text = path.read_text(encoding="utf-8-sig")
    configured = None
    found = False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(("#", "!")):
            continue
        key, separator, value = line.partition("=")
        if key.strip() != "tick-distance":
            if re.match(r"tick-distance(?:\s|:|$)", line):
                raise ValueError(f"Invalid tick-distance syntax on line {number}; expected key=value")
            continue
        if found:
            raise ValueError(f"Duplicate tick-distance on line {number}")
        if not separator or not re.fullmatch(r"[+-]?[0-9]+", value.strip()):
            raise ValueError(f"Invalid tick-distance on line {number}; expected a decimal integer")
        configured = int(value.strip())
        found = True
    return TickDistance(configured, max(4, min(12, configured)) if found else 4)
