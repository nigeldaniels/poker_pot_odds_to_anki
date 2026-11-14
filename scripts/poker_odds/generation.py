"""Bounded, seeded generation of varied postflop decision points."""
import random

from .accounting import analyze
from .models import KINDS, POSITIONS, STREETS, Action, Scenario


def generate(count: int, seed: int, street: str = 'mixed', kind: str = 'mixed',
             examples: bool = True) -> list[Scenario]:
    if not 1 <= count <= 1000:
        raise ValueError('Count must be between 1 and 1000')
    if street not in ('mixed', *STREETS) or kind not in ('mixed', *KINDS):
        raise ValueError('Unsupported street or scenario kind')
    rng = random.Random(seed)
    result, seen = [], set()
    candidates = [s for s in original_examples()
                  if examples and street in ('mixed', s.street) and kind in ('mixed', s.kind)]
    attempts = 0
    # The finite retry budget prevents a constrained request from looping indefinitely.
    while len(result) < count and attempts < count * 100:
        s = candidates.pop(0) if candidates else random_scenario(
            rng, STREETS[attempts % 3] if street == 'mixed' else street,
            KINDS[attempts % 4] if kind == 'mixed' else kind)
        attempts += 1
        analyze(s)
        if s.guid() not in seen:
            seen.add(s.guid())
            result.append(s)
    if len(result) != count:
        raise ValueError('Could not generate enough distinct questions for these filters')
    return result


def random_scenario(rng: random.Random, street: str, kind: str) -> Scenario:
    return HistoryBuilder(rng, street, kind).build()


def original_examples() -> list[Scenario]:
    return [
        Scenario('river', 50, ('UTG', 'MP', 'BTN'),
                 (Action('UTG', 'bet', 25), Action('MP', 'call')), 'BTN', 'bet'),
        Scenario('flop', 12, ('SB', 'BB', 'UTG', 'BTN'),
                 (Action('SB', 'check'), Action('BB', 'check'),
                  Action('UTG', 'bet', 8), Action('BTN', 'fold'),
                  Action('SB', 'raise', 20)), 'BB', 'check-raise'),
    ]


class HistoryBuilder:
    """Shared random sizing and action helpers for four explicit hand patterns."""

    def __init__(self, rng: random.Random, street: str, kind: str):
        self.rng, self.street, self.kind = rng, street, kind
        minimum = 3 if kind in ('check-raise', 'reraise') else 2
        selected = set(rng.sample(POSITIONS, rng.randint(minimum, 6)))
        self.players = tuple(p for p in POSITIONS if p in selected)
        self.count = len(self.players)
        self.pot = rng.choice((6, 8, 10, 12, 16, 20, 24, 30, 40, 50, 60, 80, 100))
        self.bet = max(2, round(self.pot * rng.choice((.25, 1/3, .5, 2/3, .75, 1))))
        self.raise_to = self.bet * rng.choice((2, 3, 4))
        self.actions: list[Action] = []

    def build(self) -> Scenario:
        if self.kind == 'bet':
            hero = self.facing_bet()
        elif self.kind == 'check-raise':
            hero = self.check_raise()
        elif self.kind == 'facing-raise':
            hero = self.facing_raise()
        elif self.kind == 'reraise':
            hero = self.reraise()
        else:
            raise ValueError(f'Unknown kind: {self.kind}')
        return Scenario(self.street, self.pot, self.players, tuple(self.actions),
                        self.players[hero], self.kind)

    def facing_bet(self) -> int:
        bettor = self.rng.randrange(self.count - 1)
        hero = self.rng.randrange(bettor + 1, self.count)
        for i in range(bettor):
            self.act(i, 'check')
        self.act(bettor, 'bet', self.bet)
        for i in range(bettor + 1, hero):
            self.respond(i)
        return hero

    def check_raise(self) -> int:
        bettor = self.rng.randrange(2, self.count)
        for i in range(bettor):
            self.act(i, 'check')
        self.act(bettor, 'bet', self.bet)
        for i in range(bettor + 1, self.count):
            self.respond(i)
        self.act(0, 'raise', self.raise_to)
        return 1

    def facing_raise(self) -> int:
        hero = self.rng.randrange(self.count - 1)
        raiser = self.rng.randrange(hero + 1, self.count)
        for i in range(hero):
            self.act(i, 'check')
        self.act(hero, 'bet', self.bet)
        for i in range(hero + 1, raiser):
            self.respond(i)
        self.act(raiser, 'raise', self.raise_to)
        for i in list(range(raiser + 1, self.count)) + list(range(hero)):
            self.respond(i)
        return hero

    def reraise(self) -> int:
        hero = self.rng.randrange(1, self.count)
        self.act(0, 'bet', self.bet)
        for i in range(1, hero):
            self.respond(i)
        self.act(hero, 'raise', self.raise_to)
        for i in range(hero + 1, self.count):
            self.respond(i)
        amount = self.raise_to + (self.raise_to - self.bet) * self.rng.choice((1, 2, 3))
        self.act(0, 'raise', amount)
        folded = {a.player for a in self.actions if a.kind == 'fold'}
        for i in range(1, hero):
            if self.players[i] not in folded:
                self.respond(i)
        return hero

    def act(self, i: int, kind: str, amount: int = 0) -> None:
        self.actions.append(Action(self.players[i], kind, amount))

    def respond(self, i: int) -> None:
        self.act(i, 'call' if self.rng.random() < .65 else 'fold')
