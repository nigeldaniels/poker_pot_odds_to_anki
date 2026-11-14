"""Behavioral tests; all Anki writes are isolated in temporary directories."""
import json
from pathlib import Path
import random
import tempfile
import unittest
from fractions import Fraction

from poker_odds.models import Action, Scenario, KINDS, STREETS
from poker_odds.accounting import analyze
from poker_odds.generation import generate, original_examples, random_scenario
from poker_odds.rendering import render
from poker_odds.verification import verify_manifest
from poker_odds.anki_package import write_package
try:
    from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
except ImportError:
    Collection = None


class AccountingTests(unittest.TestCase):
    def test_user_examples(self):
        river, flop = map(analyze, original_examples())
        self.assertEqual((river['pot_before_call'], river['call'], river['ratio'],
                          river['equity_fraction'], river['players_still_to_act']),
                         (100, 25, '4:1', '1/5', []))
        self.assertEqual((flop['pot_before_call'], flop['call'], flop['ratio'],
                          flop['equity_fraction'], flop['players_still_to_act']),
                         (40, 20, '2:1', '1/3', ['UTG']))

    def test_incremental_raise_and_folded_money(self):
        s = Scenario('turn', 20, ('SB', 'BB', 'UTG', 'BTN'), (
            Action('SB', 'bet', 5), Action('BB', 'call'),
            Action('UTG', 'raise', 15), Action('BTN', 'fold'),
            Action('SB', 'raise', 25), Action('BB', 'fold')), 'UTG', 'reraise')
        a = analyze(s)
        self.assertEqual(a['contributions'], {'SB': 25, 'BB': 5, 'UTG': 15, 'BTN': 0})
        self.assertEqual((a['pot_before_call'], a['call'], a['ratio'], a['equity_fraction']),
                         (65, 10, '13:2', '2/15'))
        self.assertEqual(a['players_still_to_act'], [])

    def test_illegal_actions_rejected(self):
        histories = [
            (Action('BB', 'bet', 8),),
            (Action('SB', 'bet', 8), Action('BB', 'check')),
            (Action('SB', 'bet', 8), Action('BB', 'raise', 12)),
            (Action('SB', 'call'),),
            (Action('SB', 'bet', 8), Action('BB', 'fold'), Action('BB', 'raise', 24)),
        ]
        for actions in histories:
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                analyze(Scenario('river', 20, ('SB', 'BB', 'BTN'), actions, 'BTN', 'bet'))

    def test_random_histories_against_independent_ledger(self):
        rng = random.Random(7123)
        for i in range(2400):
            s = random_scenario(rng, STREETS[i % 3], KINDS[i % 4])
            a = analyze(s)
            ledger = dict.fromkeys(s.players, 0)
            for action in s.actions:
                if action.kind in ('bet', 'raise'):
                    ledger[action.player] = action.to
                elif action.kind == 'call':
                    ledger[action.player] = max(ledger.values())
            pot = s.starting_pot + sum(ledger.values())
            cost = max(ledger.values()) - ledger[s.hero]
            self.assertEqual((a['pot_before_call'], a['call']), (pot, cost))
            self.assertEqual(Fraction(a['equity_fraction']), Fraction(cost, pot + cost))
            self.assertGreater(cost, 0)
            self.assertNotIn(s.hero, a['players_still_to_act'])

    def test_batch_identity_filters_and_bounds(self):
        first = generate(100, 314)
        self.assertEqual(first, generate(100, 314))
        self.assertEqual(len({s.guid() for s in first}), 100)
        self.assertNotEqual(first, generate(100, 315))
        for street in STREETS:
            for kind in KINDS:
                batch = generate(30, 5, street, kind)
                self.assertTrue(all(s.street == street and s.kind == kind for s in batch))
        for count in (0, -1, 1001):
            with self.assertRaises(ValueError):
                generate(count, 0)


    def test_seed_reproduces_published_example_batch(self):
        path = Path(__file__).resolve().parents[1] / 'examples/questions.json'
        manifest = json.loads(path.read_text())
        batch = generate(30, manifest['seed'])
        self.assertEqual([s.guid() for s in batch], [n['guid'] for n in manifest['notes']])
        self.assertEqual([analyze(s) for s in batch], [n['calculation'] for n in manifest['notes']])

    def test_shared_manifest_requires_profile_override(self):
        path = Path(__file__).resolve().parents[1] / 'examples/questions.json'
        with self.assertRaisesRegex(ValueError, 'supply --profile'):
            verify_manifest(path)


@unittest.skipIf(Collection is None, "Anki library not installed")
class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='poker-import-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.col = Collection(str(self.root / 'collection.anki2'))
        self.addCleanup(self.col.close)

    def test_native_import_repeat_and_existing_progress(self):
        batch = generate(30, 914)
        existing = self.add_existing_card()
        for index in range(2):
            package = self.root / f'batch-{index}.apkg'
            write_package(batch, 'Poker Pot Odds', package)
            self.import_package(package)
            self.assertEqual(self.col.note_count(), 31)
            self.assertEqual(len(self.col.find_cards('deck:"Poker Pot Odds"')), 30)
            self.assert_progress(existing.id, (2, 2, 17, 6, 3))
            self.assert_note_contents(batch)
            if index == 0:
                study = self.col.get_card(self.col.find_cards('deck:"Poker Pot Odds"')[0])
                self.set_progress(study, 22, 9, 4)
        self.assert_progress(study.id, (2, 2, 22, 9, 4))
        self.assert_manifest_results(batch)

    def test_included_example_deck_matches_manifest(self):
        examples = Path(__file__).resolve().parents[1] / 'examples'
        manifest = json.loads((examples / 'questions.json').read_text())
        self.import_package(examples / manifest['package'])
        self.assertEqual(self.col.note_count(), 30)
        self.assertEqual(self.col.db.scalar('select count(*) from revlog'), 0)
        self.assertEqual(self.col.db.scalar('select sum(reps) from cards'), 0)
        self.assertTrue(verify_manifest(examples / 'questions.json', self.root)['verified'])
        for row in manifest['notes']:
            nid = self.col.db.scalar('select id from notes where guid=?', row['guid'])
            note = self.col.get_note(nid)
            self.assertEqual((note['Question'], note['Answer']), (row['question'], row['answer']))

    def add_existing_card(self):
        note = self.col.new_note(self.col.models.by_name('Basic'))
        note['Front'], note['Back'] = 'Existing card', 'Preserve me'
        self.col.add_note(note, self.col.decks.id('Default'))
        card = self.col.get_card(note.card_ids()[0])
        self.set_progress(card, 17, 6, 3)
        return card

    def import_package(self, package):
        self.col.import_anki_package(ImportAnkiPackageRequest(
            package_path=str(package), options=ImportAnkiPackageOptions(with_scheduling=False)))

    def set_progress(self, card, due, interval, repetitions):
        # Simulate study between imports to exercise scheduling preservation.
        card.type, card.queue, card.due, card.ivl, card.reps = 2, 2, due, interval, repetitions
        self.col.update_card(card)

    def assert_progress(self, card_id, expected):
        card = self.col.get_card(card_id)
        self.assertEqual((card.type, card.queue, card.due, card.ivl, card.reps), expected)

    def assert_note_contents(self, batch):
        for scenario in batch:
            nid = self.col.db.scalar('select id from notes where guid=?', scenario.guid())
            note = self.col.get_note(nid)
            self.assertEqual((note['Question'], note['Answer']), render(scenario))

    def assert_manifest_results(self, batch):
        manifest = self.root / 'manifest.json'
        data = dict(profile=str(self.root), deck='Poker Pot Odds',
                    notes=[dict(guid=s.guid()) for s in batch])
        manifest.write_text(json.dumps(data))
        self.assertTrue(verify_manifest(manifest)['verified'])
        data['deck'] = 'Wrong deck'
        manifest.write_text(json.dumps(data))
        self.assertEqual(verify_manifest(manifest)['wrong_deck'], 30)
        data['notes'].append(dict(guid='missing-note'))
        manifest.write_text(json.dumps(data))
        self.assertEqual(verify_manifest(manifest)['missing'], 1)


if __name__ == '__main__':
    unittest.main()
