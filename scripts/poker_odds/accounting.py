"""Replay legal betting rounds and calculate the immediate price of calling."""
from fractions import Fraction

from .models import POSITIONS, STREETS, Action, Scenario


def analyze(scenario: Scenario) -> dict:
    state = BettingRound(scenario)
    for action in scenario.actions:
        state.apply(action)
    return state.result()


class BettingRound:
    """Keep street contributions separate from the queue of players owing action."""

    def __init__(self, scenario: Scenario):
        validate_scenario(scenario)
        self.scenario = scenario
        self.contributions = dict.fromkeys(scenario.players, 0)
        self.active = list(scenario.players)
        self.pending = list(scenario.players)
        self.highest_bet = self.last_raise = 0
        self.additions = []

    def apply(self, action: Action) -> None:
        if len(self.active) < 2 or not self.pending or action.player != self.pending[0]:
            raise ValueError(f'Out-of-turn action: {action}')
        invested = self.contributions[action.player]
        if action.kind in ('bet', 'raise'):
            delta = self.raise_bet(action, invested)
        else:
            delta = self.respond(action, invested)
        self.contributions[action.player] += delta
        if delta:
            self.additions.append({'player': action.player, 'amount': delta})

    def result(self) -> dict:
        hero = self.scenario.hero
        if len(self.active) < 2 or not self.pending or self.pending[0] != hero:
            raise ValueError('The stated hero is not next to act')
        call = self.highest_bet - self.contributions[hero]
        if call <= 0:
            raise ValueError('Hero must face a positive call amount')
        pot = self.scenario.starting_pot + sum(self.contributions.values())
        odds, equity = Fraction(pot, call), Fraction(call, pot + call)
        return dict(pot_before_call=pot, call=call, highest_bet=self.highest_bet,
                    hero_invested=self.contributions[hero], final_pot=pot + call,
                    ratio=f'{odds.numerator}:{odds.denominator}',
                    ratio_to_one=float(odds), equity_fraction=str(equity),
                    equity_percent=float(equity * 100),
                    players_still_to_act=self.pending[1:],
                    contributions=self.contributions.copy(), additions=list(self.additions))

    def raise_bet(self, action: Action, invested: int) -> int:
        if action.kind == 'bet' and (self.highest_bet != 0 or action.to < 1):
            raise ValueError('Invalid opening bet')
        if action.kind == 'raise' and (
                self.highest_bet == 0 or action.to < self.highest_bet + self.last_raise):
            raise ValueError('Raise must meet the full minimum increment')
        delta = action.to - invested
        self.last_raise, self.highest_bet = action.to - self.highest_bet, action.to
        # A full raise reopens action to every other live player, including callers.
        i = self.active.index(action.player)
        self.pending = self.active[i + 1:] + self.active[:i]
        return delta

    def respond(self, action: Action, invested: int) -> int:
        if action.to:
            raise ValueError('Only bets and raises specify a total contribution')
        delta = 0
        if action.kind == 'check':
            if self.highest_bet != invested:
                raise ValueError('Cannot check facing a bet')
        elif action.kind == 'fold':
            if self.highest_bet == invested:
                raise ValueError('Unnecessary fold with no outstanding bet')
            # Folded contributions remain in the pot, even though the seat leaves action.
            self.active.remove(action.player)
        elif action.kind == 'call':
            if self.highest_bet <= invested:
                raise ValueError('No outstanding bet to call')
            delta = self.highest_bet - invested
        else:
            raise ValueError(f'Unknown action: {action.kind}')
        self.pending.pop(0)
        return delta


def validate_scenario(scenario: Scenario) -> None:
    if scenario.street not in STREETS or scenario.starting_pot <= 0:
        raise ValueError('Invalid street or starting pot')
    players = scenario.players
    if not 2 <= len(players) <= 6 or len(set(players)) != len(players):
        raise ValueError('Expected 2–6 distinct positions')
    if tuple(p for p in POSITIONS if p in players) != players:
        raise ValueError('Positions must follow postflop action order')
