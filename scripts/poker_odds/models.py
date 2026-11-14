"""Internal hand-history types and stable scenario identity."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

POSITIONS = ('SB', 'BB', 'UTG', 'MP', 'CO', 'BTN')
STREETS = ('flop', 'turn', 'river')
KINDS = ('bet', 'check-raise', 'facing-raise', 'reraise')


@dataclass(frozen=True)
class Action:
    player: str
    kind: str
    to: int = 0


@dataclass(frozen=True)
class Scenario:
    street: str
    starting_pot: int
    players: tuple[str, ...]
    actions: tuple[Action, ...]
    hero: str
    kind: str

    def guid(self) -> str:
        data = asdict(self)
        data.pop('kind')
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(('poker-pot-odds-v1:' + canonical).encode()).hexdigest()[:24]
