"""Read-only verification of imported notes in the intended Anki deck."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def verify_manifest(path: Path, profile: Path | None = None) -> dict:
    manifest = json.loads(path.read_text())
    if not isinstance(manifest, dict) or not isinstance(manifest.get('notes'), list):
        raise ValueError('Manifest must be an object with a notes array')
    destination = profile or manifest.get('profile')
    if not destination:
        raise ValueError('This shared manifest has no local profile; supply --profile')
    if not isinstance(manifest.get('deck'), str) or not manifest['notes']:
        raise ValueError('Manifest must include a deck name and at least one note')
    guids = [row.get('guid') if isinstance(row, dict) else None for row in manifest['notes']]
    if any(not isinstance(guid, str) or not guid for guid in guids):
        raise ValueError('Each manifest note must have a nonempty GUID')
    collection = Path(destination).expanduser().resolve() / 'collection.anki2'
    missing, wrong_deck = [], []
    with closing(sqlite3.connect(collection.as_uri() + '?mode=ro', uri=True)) as conn:
        locations = note_locations(conn, guids)
    for guid in guids:
        if guid not in locations:
            missing.append(guid)
        elif manifest['deck'] not in locations[guid]:
            wrong_deck.append(guid)
    return dict(verified=not missing and not wrong_deck, deck=manifest['deck'],
                expected=len(manifest['notes']), missing=len(missing), wrong_deck=len(wrong_deck))


def note_locations(conn, guids: list[str]) -> dict[str, set[str]]:
    locations = {}
    # Bound SQL parameters and avoid one full-collection lookup per generated note.
    for offset in range(0, len(guids), 400):
        batch = guids[offset:offset + 400]
        placeholders = ','.join('?' for _ in batch)
        query = ('SELECT n.guid,d.name FROM notes n JOIN cards c ON c.nid=n.id '
                 f'JOIN decks d ON d.id=c.did WHERE n.guid IN ({placeholders})')
        for guid, deck in conn.execute(query, batch):
            locations.setdefault(guid, set()).add(deck.replace('\x1f', '::'))
    return locations
