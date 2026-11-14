"""Build deck packages using only a temporary Anki collection."""
from __future__ import annotations

from pathlib import Path
import tempfile

try:
    from anki.collection import Collection, DeckIdLimit, ExportAnkiPackageOptions
except ImportError:
    # Help, accounting tests, and read-only verification do not require Anki.
    Collection = None

from .models import Scenario
from .rendering import render

MODEL_ID = 1784000769123
MODEL_NAME = 'Poker Pot Odds v1'


def write_package(scenarios: list[Scenario], deck: str, destination: Path) -> None:
    if Collection is None:
        raise RuntimeError('Anki library unavailable; use the bundled Python interpreter')
    with tempfile.TemporaryDirectory(prefix='poker-pot-odds-') as temp:
        col = Collection(str(Path(temp) / 'collection.anki2'))
        try:
            model = col.models.new(MODEL_NAME)
            model['id'] = MODEL_ID
            for name in ('Question', 'Answer'):
                col.models.add_field(model, col.models.new_field(name))
            template = col.models.new_template('Pot odds')
            template['qfmt'] = '{{Question}}'
            template['afmt'] = '{{FrontSide}}<hr id="answer">{{Answer}}'
            col.models.add_template(model, template)
            model['css'] = ('.card { font-family: Arial, sans-serif; font-size: 21px; '
                            'line-height: 1.5; text-align: left; max-width: 760px; margin: 24px auto; '
                            'padding: 0 20px; } small { font-size: .75em; opacity: .75; } '
                            'hr { margin: 24px 0; }')
            # update() accepts a fixed ID; add_dict() requires an ID of zero.
            col.models.update(model)
            did = col.decks.id(deck)
            for s in scenarios:
                note = col.new_note(model)
                note.guid = s.guid()
                note['Question'], note['Answer'] = render(s)
                note.tags = ['poker', 'pot_odds', s.street, s.kind.replace('-', '_')]
                col.add_note(note, did)
            exported = col.export_anki_package(
                out_path=str(destination), limit=DeckIdLimit(did),
                options=ExportAnkiPackageOptions(with_scheduling=False, with_deck_configs=False,
                                                with_media=False, legacy=False))
            if exported != len(scenarios):
                raise RuntimeError(f'Expected {len(scenarios)} exported cards, got {exported}')
        finally:
            col.close()
