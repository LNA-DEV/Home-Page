"""The scripts behind the game pages (docs/concepts/gaming-game-pages.md):
the slug rule and the achievement-file helpers in gaming_common.py, the
one-time slug migration, and the pure halves of game-enrich.py.

No network, and the only filesystem is a temporary directory."""

import json
import tempfile
import unittest
from pathlib import Path

from _load import load

import gaming_common
import wiki_common

add_slugs = load("gaming-add-slugs")
enrich = load("game-enrich")


class Slugify(unittest.TestCase):
    def test_the_rule(self):
        cases = {
            "Life is Strange™": "life-is-strange",
            "Rocket League®": "rocket-league",
            ">observer_": "observer",
            "Pokémon HeartGold": "pokemon-heartgold",
            "WAS IST WAS: Versunkene Schätze": "was-ist-was-versunkene-schatze",
            "Straße": "strasse",
            "1-2-Switch": "1-2-switch",
            "Civilization VI : Aztec DLC": "civilization-vi-aztec-dlc",
            "#RaceDieRun": "racedierun",
        }
        for title, slug in cases.items():
            self.assertEqual(gaming_common.slugify(title), slug, title)
            self.assertRegex(slug, gaming_common.SLUG_RE)

    def test_assign_keeps_old_slugs_and_suffixes_a_same_platform_clash(self):
        games = [{"k": "1", "title": "DOOM"}, {"k": "2", "title": "DOOM"}, {"k": "3", "title": "Old"}]
        out, new, joined = gaming_common.assign_slugs(
            games, lambda g: g["k"], {"3": "kept"}, taken={"doom"})
        self.assertEqual(out, {"1": "doom", "2": "doom-2", "3": "kept"})
        self.assertEqual(new, [("1", "doom"), ("2", "doom-2")])
        self.assertEqual(joined, [("1", "doom")])


class BerlinTime(unittest.TestCase):
    def test_a_unix_timestamp_keeps_its_local_day(self):
        # 23:30 UTC on 31 March 2024 is already 1 April in Berlin (summer time).
        self.assertEqual(gaming_common.berlin_iso(1711927800), "2024-04-01T01:30:00+02:00")

    def test_iso_strings_and_unknowns(self):
        self.assertEqual(gaming_common.berlin_iso("2024-01-01T12:00:00Z"), "2024-01-01T13:00:00+01:00")
        for unknown in (None, "", 0, "0", "garbage"):
            self.assertIsNone(gaming_common.berlin_iso(unknown))


class AchievementFiles(unittest.TestCase):
    def test_localised_drops_languages_that_repeat_english(self):
        self.assertEqual(gaming_common.localised({"en": "A", "de": "A", "sv": "B"}),
                         {"en": "A", "sv": "B"})
        self.assertEqual(gaming_common.localised({"en": "", "de": ""}), {})

    def test_json_is_byte_identical_and_only_written_when_it_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            self.assertTrue(gaming_common.write_json(path, {"b": 1, "a": "ä"}))
            first = path.read_bytes()
            self.assertFalse(gaming_common.write_json(path, {"a": "ä", "b": 1}))
            self.assertEqual(path.read_bytes(), first)
            self.assertTrue(first.decode("utf-8").endswith("}\n"))
            self.assertIn("ä", first.decode("utf-8"))

    def test_icon_names(self):
        self.assertEqual(gaming_common.icon_basename("https://x/apps/1/abc.jpg?t=1"), "abc.jpg")
        self.assertEqual(gaming_common.icon_basename("https://x/apps/1/abc"), "abc.jpg")

    def test_sync_icons_downloads_the_missing_and_removes_the_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "steam" / "1"
            folder.mkdir(parents=True)
            (folder / "keep.jpg").write_bytes(b"k")
            (folder / "stale.jpg").write_bytes(b"s")
            fetched = []

            def fetch(url):
                fetched.append(url)
                return b"new"

            got, gone, failed = gaming_common.sync_icons(
                "steam", "1", ["https://x/keep.jpg", "https://x/new.jpg"],
                icon_root=root, fetch=fetch)
            self.assertEqual((got, gone, failed), (1, 1, []))
            self.assertEqual(fetched, ["https://x/new.jpg"])
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ["keep.jpg", "new.jpg"])

    def test_prune_touches_only_the_platform_and_the_dropped_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, icons = Path(tmp) / "data", Path(tmp) / "icons"
            data.mkdir()
            for name in ("steam-1.json", "steam-2.json", "gog-2.json"):
                (data / name).write_text("{}")
            (icons / "steam" / "2").mkdir(parents=True)
            (icons / "steam" / "2" / "a.jpg").write_bytes(b"x")
            removed = gaming_common.prune_achievements("steam", {"1"}, data_dir=data, icon_root=icons)
            self.assertEqual(removed, ["2"])
            self.assertEqual(sorted(p.name for p in data.iterdir()), ["gog-2.json", "steam-1.json"])
            self.assertFalse((icons / "steam" / "2").exists())


class SlugMigration(unittest.TestCase):
    TEXT = """\
# header
# - title: "Commented Example"

- title: "Rocket League"
  platform: switch
  playtimeMinutes: 1

- title: Rocket League®
  platform: epic
  appName: Sugar

- title: "Stardew Valley"
  platform: switch

- title: "Stardew Valley"
  platform: steam
  appid: 413150
"""

    def test_slugs_go_under_the_title_and_shared_titles_share_one(self):
        out, report = add_slugs.add_slugs(self.TEXT)
        self.assertIn('- title: "Rocket League"\n  slug: rocket-league\n  platform: switch', out)
        self.assertIn("- title: Rocket League®\n  slug: rocket-league\n", out)
        self.assertEqual(out.count("slug: stardew-valley"), 2)
        self.assertEqual(report["merged"], {"rocket-league": ["Rocket League", "Rocket League®"]})
        self.assertEqual(report["clashes"], {})
        self.assertIn('# - title: "Commented Example"\n', out)

    def test_a_second_run_changes_nothing(self):
        once, _ = add_slugs.add_slugs(self.TEXT)
        twice, report = add_slugs.add_slugs(once)
        self.assertEqual(once, twice)
        self.assertEqual(report["added"], [])

    def test_two_copies_on_one_platform_are_a_clash(self):
        text = '- title: "DOOM"\n  platform: steam\n\n- title: "Doom"\n  platform: steam\n'
        _, report = add_slugs.add_slugs(text)
        self.assertIn("doom", report["clashes"])


class GameEnrich(unittest.TestCase):
    def test_store_html_becomes_plain_text(self):
        self.assertEqual(enrich.plain_text("A &quot;cozy&quot;<br> farm&nbsp;game."),
                         'A "cozy" farm game.')

    def test_earliest_date_is_as_precise_as_the_statement(self):
        entity = {"claims": {"P577": [
            {"mainsnak": {"datavalue": {"value": {"time": "+2017-02-24T00:00:00Z", "precision": 11}}}},
            {"mainsnak": {"datavalue": {"value": {"time": "+2016-00-00T00:00:00Z", "precision": 9}}}},
        ]}}
        self.assertEqual(enrich.earliest_date(entity), "2016")

    def test_build_facts_keeps_every_candidate_with_its_source(self):
        entity = {"claims": {
            "P136": [{"mainsnak": {"datavalue": {"value": {"id": "Q1"}}}}],
            "P178": [{"mainsnak": {"datavalue": {"value": {"id": "Q2"}}}}],
        }}
        labels = {"Q1": {"labels": {"en": {"value": "platformer"}, "de": {"value": "Jump ’n’ Run"}}},
                  "Q2": {"labels": {"en": {"value": "Team Cherry"}}}}
        doc = enrich.build_facts("Q9", "steam-appid", entity, labels,
                                 {"en": ("Text.", "https://en.wikipedia.org/wiki/X"), "sv": ("", "u")},
                                 "367520", {"en": "Blurb."})
        self.assertEqual(doc["wikidata"], "Q9")
        self.assertEqual(doc["wikipedia"], {"en": {"text": "Text.", "url": "https://en.wikipedia.org/wiki/X"}})
        self.assertEqual(doc["genres"], [{"en": "platformer", "de": "Jump ’n’ Run"}])
        self.assertEqual(doc["developers"], ["Team Cherry"])
        self.assertEqual(doc["steam"], {"en": "Blurb."})
        self.assertEqual(doc["steam_appid"], 367520)
        json.dumps(doc)  # serialisable as-is

    def test_nothing_to_store_is_no_document(self):
        self.assertIsNone(enrich.build_facts(None, "", {}, {}, {}, None, {}))


class WikiCommon(unittest.TestCase):
    def test_abbreviations_do_not_end_a_sentence(self):
        # The case the rule was written for (dex-enrich.py): "…including L. a. agilis".
        text = ("It has subspecies including L. a. agilis and others. It lives in Europe. "
                "It is green. It is small.")
        self.assertEqual(wiki_common.trim_extract(text),
                         "It has subspecies including L. a. agilis and others. It lives in Europe. "
                         "It is green.")

    def test_a_stub_is_nothing(self):
        self.assertEqual(wiki_common.trim_extract("Too short."), "")


if __name__ == "__main__":
    unittest.main()
