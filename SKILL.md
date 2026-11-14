---
name: poker-pot-odds
description: Generate varied poker pot-odds word problems with calculated answers and create or extend a local Anki practice deck. Use for poker betting-action flashcards and pot-odds drills.
---

# Poker Pot Odds

Generate short postflop hand histories like “The river starts with 50bb in the pot. UTG bets 25bb, MP calls, and action is on BTN. What are BTN's pot odds?” Put the question on the front and the worked solution on the back of one Anki card.

## Defaults and local destination

- Unless specified otherwise, generate 30 questions in a separate **Poker Pot Odds** deck, mixing flop, turn, and river situations with bets, callers, folds, check-raises, and reraises. Include the two original examples on initial creation.
- Discover the existing Anki profile. On Linux the default is `~/.local/share/Anki2/User 1/collection.anki2`; use `--profile` for another profile or installation. Decks are logical groups inside that collection, not separate database files. Save `.apkg` packages beside it, then import into the same profile. Never replace `collection.anki2` or use a collection-replacement `.colpkg`.
- Honor a different deck, count, profile, or output folder when specified. Never silently create an empty substitute profile.
- A request to generate/create/add a deck authorizes this local generation and import. A request only for a preview does not authorize import. Do not sync to AnkiWeb unless requested.

## Generate

Resolve commands relative to this skill directory. The script finds Anki's bundled Python on Linux, or accepts `ANKI_PYTHON` and `ANKI_PACKAGES` for another installation. It uses Anki's own library to build a package in a temporary collection and never opens the user's collection for writing. See [README.md](README.md) for installation and runtime details.

```bash
python3 scripts/pot_odds.py generate --count 30 --deck 'Poker Pot Odds'
```

Useful options:

- `--street flop|turn|river|mixed` (default mixed).
- `--kind bet|check-raise|facing-raise|reraise|mixed` (default mixed).
- `--seed INTEGER` to reproduce a batch; omit for new variations.
- `--no-examples` for subsequent batches or entirely new problems. Example inclusion respects street/kind filters.
- `--profile '/path/to/Anki2/Profile'` and `--output-dir '/path/to/folder'` to change destinations.
- `--open` to open the package in Anki's import dialog. Opening the dialog is not proof of import.

Each batch produces a uniquely named `.apkg` and `.json` manifest with questions, answers, actions, calculations, and stable note GUIDs. Repeating a scenario keeps its GUID; repeated imports do not duplicate those notes. Distinct scenarios with the same numerical answer are valid practice variations.

For requests the generator does not support (e.g. side pots or all-ins), extend the calculation and validation first or explain the limitation. Do not label standard-pot questions as unsupported scenarios.

## Import and verify

Use Anki's normal package import into the existing profile. Prefer an already available AnkiConnect integration; otherwise open the package through the installed `anki` launcher and complete the **Import** dialog through desktop accessibility. Where installed on Linux, desktop accessibility is available through `gi.repository.Atspi` in the system Python. Restrict clicks to the identified Anki import window. Preserve unsaved editor input; never choose **Discard** to make an import proceed. Canceling a discard prompt with **Keep Editing** is safe, but do not close the editor afterward.

After import, verify every generated GUID is present in the intended deck:

```bash
python3 scripts/pot_odds.py verify '/absolute/path/to/batch.json'
```

This reads the live database with SQLite `mode=ro`, including committed WAL data. Success means the expected notes actually have cards in that deck. If the import UI remains blocked, stop retrying, provide the ready-to-import package, and accurately report that import is pending. A saved `.apkg` alone is not an installed deck.

## Question and answer rules

- The starting pot is at the start of the named street; all stated actions occur afterward. Position order is SB, BB, UTG, MP, CO, BTN with absent seats skipped. Two remaining players are seats at a larger table, not a special heads-up blind structure.
- Track each player's total contribution on this street. “Raises to 20bb” is a total of 20bb; add only the increase since that player's last action. The caller owes the highest contribution minus their own contribution so far. Previously invested chips remain in the pot.
- Let **P** be the entire pot before the pending call and **C** its additional cost. Pot odds are **P:C** (reward:risk). Break-even equity for this immediate price is **C / (P + C)**. Show the exact reduced ratio and a percentage, rounded only for display.
- Exclude future calls from P, but include money from players who subsequently fold. Ensure legal action order and full minimum raises. The validator rejects impossible action histories.
- State that there is no rake, no side pot, and everyone can cover the bets. On the answer, flag players still to act after the call. On flop/turn, note that future betting can change the value of calling. Pot odds alone do not decide whether a real call is profitable.
- Do not add board cards, hand-strength judgments, implied odds, or betting recommendations unless requested; these questions train accounting and immediate pot odds.

When modifying the generator, run `python3 -m unittest discover -s tests -v` with `PYTHONPATH=scripts`. Run it again with Anki's bundled Python and both `scripts` and its `app_packages` directory on `PYTHONPATH` to include native import tests. Tests cover the original examples, incremental calls, folded money, illegal actions, randomized histories, and real package import/deduplication in temporary collections.

The repository includes [a 30-card example deck](examples/Poker-Pot-Odds-30-cards.apkg) and [its questions](examples/questions.json). The shared JSON intentionally omits a local profile; verify it with `verify examples/questions.json --profile /path/to/Anki2/Profile`.

Anki reference: [Packaged deck import](https://docs.ankiweb.net/importing/packaged-decks.html).
