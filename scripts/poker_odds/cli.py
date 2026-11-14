"""Command parsing and orchestration; domain logic lives in focused modules."""
import argparse
import json
from pathlib import Path

from .batch import create_batch
from .models import KINDS, STREETS
from .runtime import default_profile, ensure_anki_python, open_package
from .verification import verify_manifest


def main(entrypoint: Path) -> int:
    parser = argument_parser()
    args = parser.parse_args()
    if args.command == 'verify':
        result = verify_manifest(args.manifest.expanduser().resolve(), args.profile)
        print(json.dumps(result, indent=2))
        return 0 if result['verified'] else 1
    profile = validate_generation(args, parser)
    ensure_anki_python(entrypoint)
    result = create_batch(args, profile)
    if args.open:
        open_package(Path(result['package']), profile)
        result['import_dialog_requested'] = True
    print(json.dumps(result, indent=2))
    return 0


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate pot-odds drills as native Anki packages.')
    subs = parser.add_subparsers(dest='command', required=True)
    gen = subs.add_parser('generate', help='Build an .apkg and an auditable JSON manifest')
    gen.add_argument('--count', type=int, default=30)
    gen.add_argument('--deck', default='Poker Pot Odds')
    gen.add_argument('--seed', type=int)
    gen.add_argument('--street', choices=('mixed', *STREETS), default='mixed')
    gen.add_argument('--kind', choices=('mixed', *KINDS), default='mixed')
    gen.add_argument('--no-examples', action='store_true')
    gen.add_argument('--profile', type=Path, default=default_profile())
    gen.add_argument('--output-dir', type=Path)
    gen.add_argument('--open', action='store_true', help='Open the import dialog; does not confirm import')
    verify = subs.add_parser('verify', help='Read-only check of imported cards in the live collection')
    verify.add_argument('manifest', type=Path)
    verify.add_argument('--profile', type=Path, help='Override the manifest profile for shared examples')
    return parser


def validate_generation(args, parser: argparse.ArgumentParser) -> Path:
    if not 1 <= args.count <= 1000:
        parser.error('--count must be between 1 and 1000')
    if not args.deck.strip() or any(not part.strip() for part in args.deck.split('::')):
        parser.error('--deck must contain nonempty deck names')
    profile = args.profile.expanduser().resolve()
    if not (profile / 'collection.anki2').is_file():
        parser.error(f'Existing Anki collection not found in {profile}; supply --profile')
    return profile
