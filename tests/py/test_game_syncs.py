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


SWITCH = """\
- title: "Stardew Valley"
  slug: stardew-valley
  platform: switch
  playtimeMinutes: 3600
"""


def steam_game(appid=413150, title="Stardew Valley", **over):
    g = {"appid": appid, "title": title, "playtimeMinutes": 900}
    g.update(over)
    return g


class Slugs(unittest.TestCase):
    """A slug is a page URL: written once, second line of the entry, never
    recomputed (docs/concepts/gaming-game-pages.md §2)."""

    def test_a_new_game_gets_a_slug_from_its_title_on_the_second_line(self):
        out, summary = steam.rebuild(MANUAL, [steam_game(620, "Portal 2")])
        self.assertIn('- title: Portal 2\n  slug: portal-2\n  platform: steam', out)
        self.assertEqual(summary["new_slugs"], [("620", "portal-2")])

    def test_a_steam_rename_keeps_the_slug(self):
        first, _ = steam.rebuild(MANUAL, [steam_game(319630, "Life is Strange")])
        second, summary = steam.rebuild(first, [steam_game(319630, "Life is Strange™ Remastered")])
        self.assertIn("  slug: life-is-strange\n", second)
        self.assertEqual(summary["new_slugs"], [])

    def test_a_hand_edited_slug_survives(self):
        first, _ = steam.rebuild(MANUAL, [steam_game(620, "Portal 2")])
        edited = first.replace("slug: portal-2", "slug: portal-two")
        second, _ = steam.rebuild(edited, [steam_game(620, "Portal 2")])
        self.assertIn("slug: portal-two", second)
        self.assertNotIn("slug: portal-2\n", second)

    def test_a_copy_on_another_platform_is_joined_and_reported(self):
        out, summary = steam.rebuild(SWITCH, [steam_game()])
        self.assertEqual(out.count("slug: stardew-valley"), 2)
        self.assertEqual(summary["joined"], [("413150", "stardew-valley")])

    def test_two_games_of_one_platform_never_share_a_slug(self):
        out, _ = steam.rebuild("", [steam_game(1, "DOOM"), steam_game(2, "DOOM")])
        self.assertIn("slug: doom\n", out)
        self.assertIn("slug: doom-2\n", out)

    def test_epic_and_gog_write_slugs_too(self):
        text, _ = epic.rebuild(SWITCH, [{"app_name": "Sugar", "title": "Rocket League®",
                                         "playtimeMinutes": 5}])
        self.assertIn("- title: Rocket League®\n  slug: rocket-league\n  platform: epic", text)
        text, summary = gog.rebuild(SWITCH, [{"app_name": "1", "title": "Stardew Valley",
                                              "playtimeMinutes": 5}])
        self.assertEqual(summary["joined"], [("1", "stardew-valley")])

    def test_a_second_run_is_byte_identical_with_slugs(self):
        once, _ = steam.rebuild(SWITCH, [steam_game()])
        twice, _ = steam.rebuild(once, [steam_game()])
        self.assertEqual(once, twice)


class SkippedAchievements(unittest.TestCase):
    """A game whose achievements were not fetched keeps its counts — its file is
    kept too, and the card and the page must keep agreeing."""

    def test_steam_carries_the_old_counts_over(self):
        first, _ = steam.rebuild("", [steam_game(achievementsUnlocked=10, achievementsTotal=49)])
        second, _ = steam.rebuild(first, [steam_game(achievementsSkipped=True)])
        self.assertIn("achievementsUnlocked: 10\n  achievementsTotal: 49", second)

    def test_a_fetched_game_takes_the_new_counts(self):
        first, _ = steam.rebuild("", [steam_game(achievementsUnlocked=10, achievementsTotal=49)])
        second, _ = steam.rebuild(first, [steam_game(achievementsUnlocked=11, achievementsTotal=49)])
        self.assertIn("achievementsUnlocked: 11", second)

    def test_gog_carries_the_old_counts_over(self):
        g = {"app_name": "7", "title": "Hollow Knight", "playtimeMinutes": 5,
             "ach_unlocked": 3, "ach_total": 63}
        first, _ = gog.rebuild("", [g])
        second, _ = gog.rebuild(first, [dict(g, ach_unlocked=None, ach_total=None, ach_skipped=True)])
        self.assertIn("achievementsUnlocked: 3\n  achievementsTotal: 63", second)


class SteamAchievementDocument(unittest.TestCase):
    PLAYER = [
        {"apiname": "B", "achieved": 1, "unlocktime": 1549926843, "name": "Bee", "description": "b"},
        {"apiname": "A", "achieved": 0, "unlocktime": 0, "name": "Ay", "description": "a"},
        {"apiname": "C", "achieved": 1, "unlocktime": 0, "name": "Cee", "description": ""},
    ]
    SCHEMAS = {
        "en": [
            {"name": "A", "displayName": "Ay", "description": "a", "hidden": 0,
             "icon": "https://cdn.example/apps/1/aaa.jpg"},
            {"name": "B", "displayName": "Bee", "description": "b", "hidden": 0,
             "icon": "https://cdn.example/apps/1/bbb.jpg"},
            {"name": "C", "displayName": "Cee", "hidden": 1,
             "icon": "https://cdn.example/apps/1/ccc.jpg"},
        ],
        "de": [{"name": "A", "displayName": "Äh", "description": "a"},
               {"name": "B", "displayName": "Bee", "description": "b-de"}],
        "sv": [],
    }

    def doc(self):
        return steam.build_steam_achievements(1, self.PLAYER, self.SCHEMAS, {"A": 12.345, "B": 50})

    def test_one_row_per_player_achievement_in_schema_order(self):
        doc, _ = self.doc()
        self.assertEqual([a["key"] for a in doc["achievements"]], ["A", "B", "C"])

    def test_only_real_translations_are_stored(self):
        doc, _ = self.doc()
        a, b, _ = doc["achievements"]
        self.assertEqual(a["name"], {"en": "Ay", "de": "Äh"})
        self.assertEqual(b["name"], {"en": "Bee"})  # German equals English: no German
        self.assertEqual(b["description"], {"en": "b", "de": "b-de"})

    def test_hidden_achievements_have_no_description(self):
        doc, _ = self.doc()
        c = doc["achievements"][2]
        self.assertTrue(c["hidden"])
        self.assertNotIn("description", c)

    def test_unlocks_are_dated_in_berlin_and_zero_means_unknown(self):
        doc, _ = self.doc()
        a, b, c = doc["achievements"]
        self.assertNotIn("achieved", a)
        # 2019-02-11 23:14:03 UTC is already the 12th in Berlin.
        self.assertEqual(b["unlocked"], "2019-02-12T00:14:03+01:00")
        self.assertTrue(c["achieved"])
        self.assertNotIn("unlocked", c)

    def test_percentages_are_rounded_and_icons_are_local_refs(self):
        doc, urls = self.doc()
        a = doc["achievements"][0]
        self.assertEqual(a["percent"], 12.3)
        self.assertEqual(a["icon"], "images/games/achievements/steam/1/aaa.jpg")
        self.assertEqual(len(urls), 3)


class GogAchievementDocument(unittest.TestCase):
    ITEMS = [
        {"achievement_key": "K1", "name": "First", "description": "d", "visible": True,
         "image_url_unlocked": "https://images.gog.com/x_gac_60.jpg",
         "image_url_locked": "https://images.gog.com/y_gac_60.jpg",
         "date_unlocked": "2024-03-01T10:00:00+0000", "rarity": 42.123},
        {"achievement_key": "K2", "name": "Secret", "description": "", "visible": False,
         "image_url_unlocked": "", "image_url_locked": "https://images.gog.com/z_gac_60.jpg",
         "date_unlocked": None},
    ]

    def test_fields_map_to_the_shared_shape(self):
        doc, urls = gog.build_gog_achievements("1207664663", self.ITEMS)
        first, secret = doc["achievements"]
        self.assertTrue(first["achieved"])
        self.assertEqual(first["unlocked"], "2024-03-01T11:00:00+01:00")
        self.assertEqual(first["percent"], 42.1)
        self.assertTrue(secret["hidden"])
        self.assertEqual(secret["icon"], "images/games/achievements/gog/1207664663/z_gac_60.jpg")
        self.assertEqual(len(urls), 2)
        self.assertNotIn("percent", secret)


if __name__ == "__main__":
    unittest.main()
