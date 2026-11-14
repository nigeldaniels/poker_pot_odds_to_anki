# Poker pot odds to Anki

A Codex skill and Python program that generate poker pot-odds questions and turn them into an Anki deck. Each card has a betting scenario on the front and a worked answer on the back: the current pot, additional call amount, reward-to-risk ratio, and break-even equity.

## Try the example deck

[Download the 30-card example deck](https://github.com/nigeldaniels/poker_pot_odds_to_anki/raw/refs/heads/main/examples/Poker-Pot-Odds-30-cards.apkg), then open it in Anki or choose **File → Import**. Complete the Import dialog to add **Poker Pot Odds** to your current profile. Preserve any unfinished card in an open editor before closing it.

The package includes the two original examples:

| Scenario | Pot before calling | Call | Pot odds | Break-even equity |
| --- | ---: | ---: | ---: | ---: |
| River starts at 50bb; UTG bets 25bb; MP calls; action on BTN | 100bb | 25bb | 4:1 | 20% |
| Flop starts at 12bb; SB/BB check; UTG bets 8bb; BTN folds; SB raises to 20bb; action on BB | 40bb | 20bb | 2:1 | 33.33% |

In the second example, UTG still has to act after BB. The answer highlights that distinction. All 30 questions and their calculations are also available in [examples/questions.json](examples/questions.json), without local profile paths or personal study history.

## Install the Codex skill

Clone this repository and link its root into your Codex skills directory:

```bash
git clone https://github.com/nigeldaniels/poker_pot_odds_to_anki.git
cd poker_pot_odds_to_anki
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD" "${CODEX_HOME:-$HOME/.codex}/skills/poker-pot-odds"
```

The link command intentionally fails if a skill already exists at that location. Keep an existing installation or move it aside before replacing it.

Then ask Codex:

> Use $poker-pot-odds to generate 30 questions and import them into my Anki profile.

Or:

> Use $poker-pot-odds to add 50 more river questions to Poker Pot Odds.

The skill instructions are in [SKILL.md](SKILL.md). A deck request authorizes local generation/import; it does not sync anything to AnkiWeb.

## Run the program directly

Requires Python 3.10+ and Anki's Python library. Linux bundled Anki installations are discovered automatically; no separate Python packages are needed when a compatible bundle is installed. Tested with Anki **26.09.4** on Linux.

```bash
python3 scripts/pot_odds.py generate --count 30 --deck 'Poker Pot Odds'
```

By default, output is saved beside `collection.anki2` in the conventional `User 1` profile. Existing decks share that collection; they are not separate database files. Use `--profile` for a renamed profile, Flatpak installation, or custom data folder:

```bash
python3 scripts/pot_odds.py generate \
  --profile "$HOME/.local/share/Anki2/User 1" \
  --count 50 --street river --no-examples --open
```

The command prints the package and manifest paths. `--open` requests Anki's import dialog; it does **not** prove that import completed. Launch errors are saved in a sibling `.import.log` file. After completing import:

```bash
python3 scripts/pot_odds.py verify /absolute/path/to/generated-batch.json
```

To verify the included example deck after importing it:

```bash
python3 scripts/pot_odds.py verify examples/questions.json \
  --profile "$HOME/.local/share/Anki2/User 1"
```

Useful options:

| Option | Purpose |
| --- | --- |
| `--count 30` | Generate 1–1,000 distinct questions |
| `--street mixed` | Choose `mixed`, `flop`, `turn`, or `river` |
| `--kind mixed` | Choose `mixed`, `bet`, `check-raise`, `facing-raise`, or `reraise` |
| `--seed 123` | Reproduce a question batch |
| `--no-examples` | Omit the two fixed examples when adding another batch |
| `--deck 'Name'` | Choose the logical destination deck |
| `--output-dir /path` | Save packages somewhere other than the profile folder |
| `--open` | Open the package in Anki for import |

If automatic runtime discovery fails, run with an interpreter that already has `anki` installed, or set `ANKI_PYTHON` to the bundled interpreter and `ANKI_PACKAGES` to its `app_packages` directory. Other operating systems and Anki versions have not been tested.

## Calculation and data flow

`scripts/pot_odds.py` → CLI validation → scenario generation → action replay → HTML rendering → temporary Anki collection → `.apkg` and JSON manifest. Import goes through Anki itself; verification reads the real collection with SQLite `mode=ro`.

For a pot of **P** before calling and an additional call cost of **C**, pot odds are **P:C**, and break-even equity is **C / (P + C)**.

- “Raises to” means the player's total contribution on that street. Only the increase is added to the pot.
- Money already invested, including folded players' money, stays in the pot. The current call cost excludes the hero's earlier contribution.
- The generator validates turn order and full minimum raises, and distinguishes closed action from players still waiting to act.
- Stable question GUIDs and a fixed note-type ID allow repeated imports without duplicating identical notes. Package exports contain no review progress or deck presets.
- All database writes happen in temporary build collections, which are closed and removed afterward. Verification closes its read-only connection and batches lookups in groups of 400.
- Generation is bounded to 1,000 questions and a finite deduplication retry budget. Each scenario has at most six players; there are no background generation services.

These are immediate pot-price drills with sufficient stacks, no rake, no all-ins, and no side pots. Flop/turn answers note that future betting affects the value of calling. The questions do not estimate hand equity or recommend whether to call.

## Source map and tests

| File | Lines | Responsibility |
| --- | ---: | --- |
| `scripts/pot_odds.py` | 15 | CLI entrypoint and expected-error reporting |
| `scripts/poker_odds/cli.py` | 56 | Argument parsing and command orchestration |
| `scripts/poker_odds/batch.py` | 36 | Package/manifest creation workflow |
| `scripts/poker_odds/models.py` | 33 | Hand-history values and stable GUIDs |
| `scripts/poker_odds/generation.py` | 130 | Seeded hand templates and batch generation |
| `scripts/poker_odds/accounting.py` | 97 | Betting state, legal actions, and exact ratios |
| `scripts/poker_odds/rendering.py` | 47 | Question and worked-answer HTML |
| `scripts/poker_odds/anki_package.py` | 54 | Native package export from a temporary collection |
| `scripts/poker_odds/runtime.py` | 63 | Runtime discovery, profile defaults, and GUI launch |
| `scripts/poker_odds/verification.py` | 43 | Read-only verification of imported GUIDs/decks |
| `scripts/poker_odds/__init__.py` | 1 | Package marker |
| `tests/test_pot_odds.py` | 180 | Accounting, reproducibility, package import, and progress preservation |

Run accounting tests using the standard library:

```bash
PYTHONPATH=scripts python3 -m unittest discover -s tests -v
```

Native Anki tests are explicitly skipped when its library is unavailable. To include them using the tested Linux bundle:

```bash
PYTHONPATH=scripts:/usr/local/share/anki/app_packages \
  /usr/local/share/anki/python/bin/python3.13 \
  -m unittest discover -s tests -v
```

All nine tests passed with the bundled Anki runtime. Tests cover the original examples, incremental raises, folded contributions, illegal histories, 2,400 randomized action histories, filtering/reproducibility, repeat imports, and preservation of existing review progress. Native tests use temporary collections, never your study collection.

Local `AGENTS.md` instructions are deliberately ignored by Git and are not included in this repository.
