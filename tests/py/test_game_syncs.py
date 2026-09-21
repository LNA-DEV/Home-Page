"""The three game syncs rebuild their own platform block and nothing else.

Each one owns exactly the entries of its platform, rewrites them as a marked
block last in data/gaming.yaml, and must leave every other line byte-for-byte
untouched — hand-added games are safe, and the human-owned fields on a synced
entry survive the sync.

`rebuild()` is pure in all three: current file text + fetched games → new text.
No network, no filesystem.

Note the two spellings: a fetched game dict uses snake_case internally
(`app_name`, `ach_total`), while the YAML key it is written out as is `appName`.
The fixtures below use the internal shape, because that is what rebuild() takes.
"""

import unittest

from _load import load

steam = load("sync-steam")
epic = load("sync-epic")
gog = load("sync-gog")

MANUAL = """\
# A header comment.

- title: A Hand-Added Game
  platform: manual
  playtimeMinutes: 120
  rating: 5
  notes: "played on a friend's console"
"""


class SteamRebuild(unittest.TestCase):
    def games(self, **over):
        g = {"appid": 620, "title": "Portal 2", "playtimeMinutes": 900,
             "lastPlayed": "2026-01-02", "cover": "images/games/covers/Portal 2.jpg"}
        g.update(over)
        return [g]

    def test_a_non_steam_entry_is_preserved_verbatim(self):
        out, summary = steam.rebuild(MANUAL, self.games())
        self.assertIn("- title: A Hand-Added Game", out)
        self.assertIn('  notes: "played on a friend\'s console"', out)
        self.assertIn("# A header comment.", out)
        self.assertEqual(summary["manual"], 1)

    def test_human_fields_survive_a_sync(self):
        first, _ = steam.rebuild(MANUAL, self.games())
        edited = first.replace("  platform: steam", "  platform: steam\n  rating: 4\n  tags: [puzzle]")
        second, _ = steam.rebuild(edited, self.games(playtimeMinutes=1000))
        self.assertIn("  rating: 4", second)
        self.assertIn("  tags: [puzzle]", second)
        self.assertIn("  playtimeMinutes: 1000", second)

    def test_a_delisted_game_is_pruned(self):
        first, _ = steam.rebuild(MANUAL, self.games())
        second, summary = steam.rebuild(first, [])
        self.assertNotIn("Portal 2", second)
        self.assertEqual(summary["pruned"], ["620"])
        self.assertIn("- title: A Hand-Added Game", second)

    def test_a_new_game_is_added(self):
        _, summary = steam.rebuild(MANUAL, self.games())
        self.assertEqual(summary["added"], ["620"])

    def test_the_marker_never_accumulates(self):
        text = MANUAL
        for _ in range(3):
            text, _ = steam.rebuild(text, self.games())
        self.assertEqual(text.count(steam.STEAM_MARKER), 1)

    def test_a_second_run_with_the_same_input_is_byte_identical(self):
        once, _ = steam.rebuild(MANUAL, self.games())
        twice, _ = steam.rebuild(once, self.games())
        self.assertEqual(once, twice)

    def test_the_block_is_written_last(self):
        out, _ = steam.rebuild(MANUAL, self.games())
        self.assertLess(out.index("A Hand-Added Game"), out.index(steam.STEAM_MARKER))


class EpicRebuild(unittest.TestCase):
    def games(self, **over):
        g = {"app_name": "Fortnite", "title": "Fortnite", "playtimeMinutes": 30}
        g.update(over)
        return [g]

    def test_it_keys_on_app_name_and_leaves_steam_alone(self):
        steam_text, _ = steam.rebuild(MANUAL, [
            {"appid": 620, "title": "Portal 2", "playtimeMinutes": 900}])
        out, _ = epic.rebuild(steam_text, self.games())
        self.assertIn("Portal 2", out)
        self.assertIn(steam.STEAM_MARKER, out)
        self.assertIn("Fortnite", out)

    def test_human_fields_survive_keyed_on_appName(self):
        first, _ = epic.rebuild(MANUAL, self.games())
        edited = first.replace("  platform: epic", "  platform: epic\n  rating: 3")
        second, _ = epic.rebuild(edited, self.games(playtimeMinutes=60))
        self.assertIn("  rating: 3", second)
        self.assertIn("  playtimeMinutes: 60", second)

    def test_no_achievements_are_emitted(self):
        # Epic closed the achievement-progress API in January 2025.
        out, _ = epic.rebuild(MANUAL, self.games())
        self.assertNotIn("achievementsTotal", out)

    def test_a_second_run_is_byte_identical(self):
        once, _ = epic.rebuild(MANUAL, self.games())
        twice, _ = epic.rebuild(once, self.games())
        self.assertEqual(once, twice)


class GogRebuild(unittest.TestCase):
    def games(self, **over):
        g = {"app_name": "1207658930", "title": "The Witcher", "playtimeMinutes": 42,
             "ach_unlocked": 3, "ach_total": 10}
        g.update(over)
        return [g]

    def test_achievements_are_emitted(self):
        # The win over Epic: GOG exposes them.
        out, _ = gog.rebuild(MANUAL, self.games())
        self.assertIn("achievementsTotal: 10", out)
        self.assertIn("achievementsUnlocked: 3", out)

    def test_human_fields_survive(self):
        first, _ = gog.rebuild(MANUAL, self.games())
        edited = first.replace("  platform: gog", "  platform: gog\n  rating: 5")
        second, _ = gog.rebuild(edited, self.games(playtimeMinutes=50))
        self.assertIn("  rating: 5", second)

    def test_a_second_run_is_byte_identical(self):
        once, _ = gog.rebuild(MANUAL, self.games())
        twice, _ = gog.rebuild(once, self.games())
        self.assertEqual(once, twice)


class ThreeBlocksCoexist(unittest.TestCase):
    def test_each_sync_touches_only_its_own_platform(self):
        text = MANUAL
        text, _ = steam.rebuild(text, [{"appid": 620, "title": "Portal 2", "playtimeMinutes": 900}])
        text, _ = epic.rebuild(text, [{"app_name": "Fortnite", "title": "Fortnite", "playtimeMinutes": 30}])
        text, _ = gog.rebuild(text, [{"app_name": "1207658930", "title": "The Witcher", "playtimeMinutes": 42}])
        for needle in ("A Hand-Added Game", "Portal 2", "Fortnite", "The Witcher"):
            self.assertIn(needle, text)

        # Running one again must not disturb the other two.
        again, _ = steam.rebuild(text, [{"appid": 620, "title": "Portal 2", "playtimeMinutes": 950}])
        for needle in ("A Hand-Added Game", "Fortnite", "The Witcher"):
            self.assertIn(needle, again)
        self.assertIn("playtimeMinutes: 950", again)


class SharedShape(unittest.TestCase):
    def test_all_three_own_the_same_human_fields(self):
        self.assertEqual(steam.HUMAN_FIELDS, epic.HUMAN_FIELDS)
        self.assertEqual(steam.HUMAN_FIELDS, gog.HUMAN_FIELDS)
        self.assertIn("extraMinutes", steam.HUMAN_FIELDS)


if __name__ == "__main__":
    unittest.main()
