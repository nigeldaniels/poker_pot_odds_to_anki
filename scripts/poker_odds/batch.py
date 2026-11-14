"""Orchestrate generation, package export, and the versioned batch manifest."""
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import random
import re

from .accounting import analyze
from .anki_package import write_package
from .generation import generate
from .rendering import render


def create_batch(args, profile: Path) -> dict:
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2**63)
    scenarios = generate(args.count, seed, args.street, args.kind, not args.no_examples)
    output = (args.output_dir or profile).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^A-Za-z0-9_-]+', '-', args.deck).strip('-') or 'poker-pot-odds'
    stem = f'{slug}-{datetime.now():%Y%m%d-%H%M%S-%f}'
    package, manifest_path = output / (stem + '.apkg'), output / (stem + '.json')
    notes = [serialize_note(s) for s in scenarios]
    manifest = dict(format_version=1, deck=args.deck, profile=str(profile), seed=seed,
                    package=str(package), notes=notes)
    write_package(scenarios, args.deck, package)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    return dict(deck=args.deck, cards=len(scenarios), seed=seed, package=str(package),
                manifest=str(manifest_path), imported=False)


def serialize_note(scenario) -> dict:
    # Keep the external JSON format explicit rather than exposing service state.
    question, answer = render(scenario)
    return dict(guid=scenario.guid(), scenario=asdict(scenario), question=question,
                answer=answer, calculation=analyze(scenario))
