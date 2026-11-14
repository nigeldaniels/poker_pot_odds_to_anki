"""HTML question fronts and worked-answer backs."""
from __future__ import annotations

from .accounting import analyze
from .models import Scenario


def render(s: Scenario) -> tuple[str, str]:
    a = analyze(s)
    lines = []
    verbs = {'check': 'checks', 'call': 'calls', 'fold': 'folds'}
    for action in s.actions:
        detail = verbs.get(action.kind)
        if detail is None:
            detail = (f'bets {action.to}bb' if action.kind == 'bet'
                      else f'raises to {action.to}bb total')
        lines.append(f'{action.player} {detail}.')
    question = (f'At the start of the {s.street}, there is <b>{s.starting_pot}bb</b> '
                f'in the pot with {len(s.players)} players remaining: '
                f'{", ".join(s.players)}.<br><br>' + '<br>'.join(lines) +
                f'<br><br>Action is on us in <b>{s.hero}</b>. '
                'What are our immediate pot odds and break-even equity?'
                '<br><br><small>Ignore rake. Everyone can cover all bets; no side pots.</small>')
    terms = ' + '.join([str(s.starting_pot)] + [str(x['amount']) for x in a['additions']])
    ratio = a['ratio']
    if not ratio.endswith(':1'):
        ratio += f' (approximately {a["ratio_to_one"]:.2f}:1)'
    answer = (f'<b>Pot odds: {ratio}</b><br>'
              f'<b>Break-even equity: {a["equity_percent"]:.2f}%</b>'
              f'<br><br>Pot before our call: {terms} = <b>{a["pot_before_call"]}bb</b>.'
              f'<br>Additional call: {a["highest_bet"]} − {a["hero_invested"]} '
              f'= <b>{a["call"]}bb</b>.'
              f'<br>Reward:risk = {a["pot_before_call"]}:{a["call"]} = {a["ratio"]}.'
              f'<br>Equity = {a["call"]} / ({a["pot_before_call"]} + {a["call"]}) '
              f'= {a["equity_percent"]:.2f}%.')
    if a['hero_invested']:
        answer += '<br>Our earlier contribution is already in the pot; only the extra call is the cost.'
    pending = a['players_still_to_act']
    if pending:
        answer += ('<br><br>Calling does not close the action. Still to act: '
                   + ', '.join(pending) + '. They may fold, call, or raise. '
                   'Do not count hypothetical future calls in the current pot.')
    else:
        answer += '<br><br>Our call closes the betting on this street.'
    if s.street != 'river':
        answer += ' Future betting can change the value of calling; this is the immediate price only.'
    return question, answer
