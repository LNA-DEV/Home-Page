"""The three game syncs rebuild their own platform block and nothing else.

Each one owns exactly the entries of its platform, rewrites them as a marked
block last in data/gaming.yaml, and must leave every other line byte-for-byte
untouched — hand-added games are safe, and the human-owned fields on a synced
entry survive the sync.

`rebuild()` is pure in all three: current file text + fetched games → new text.
No network, no filesystem. So is `merge_games()` in the Epic and GOG syncs,
which folds the library, every device's snapshot and the cloud into those games
— the Epic sum and the GOG max across devices are tested here; the snapshots
themselves in test_gaming_devices.py.

Note the two spellings: a fetched game dict uses snake_case internally
(`app_name`, `ach_total`), while the YAML key it is written out as is `appName`.
The fixtures below use the internal shape, because that is what rebuild() takes.
"""

import contextlib
import io
import unittest
from unittest import mock

from _load import load

import gaming_devices as gd

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


def snapshots(**by_device):
    """{device: snapshot} as gaming_devices.collect() returns it; each argument is
    {"epic": {...}, "gog": {...}} for one device."""
    return {d: {"schema": 1, "device": d,
                "stores": {"epic": s.get("epic", {}), "gog": s.get("gog", {})}}
            for d, s in by_device.items()}


def quiet(fn, *a, **k):
    with contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


CELESTE_LIB = {"Salt": {"title": "Celeste", "cover": "https://cdn/Salt.jpg",
                        "link": "https://store/Salt"}}


class EpicDevices(unittest.TestCase):
    """Epic playtime via Heroic lives only on the machine that played it, so every
    device's snapshot is summed — each session is on exactly one machine."""

    def merged(self, library, snaps, cloud):
        return {g["app_name"]: g for g in quiet(
            epic.merge_games, library, gd.per_game(snaps, "epic"), cloud)}

    def test_devices_and_cloud_sum_and_the_newest_date_wins(self):
        snaps = snapshots(
            pc={"epic": {"Salt": {"minutes": 14, "title": "Celeste", "lastPlayed": "2026-02-26"}}},
            laptop={"epic": {"Salt": {"minutes": 300, "title": "Celeste", "lastPlayed": "2026-09-20"}}})
        g = self.merged(CELESTE_LIB, snaps, {"Salt": 60})["Salt"]
        self.assertEqual(g["playtimeMinutes"], 374)
        self.assertEqual(g["lastPlayed"], "2026-09-20")

    def test_with_one_device_it_is_the_old_direct_read(self):
        # Before devices: minutes = heroic + cloud, lastPlayed = heroic's date,
        # title/cover/link from the library.
        snaps = snapshots(pc={"epic": {"Salt": {"minutes": 14, "title": "Celeste",
                                                "lastPlayed": "2026-02-26"}}})
        g = self.merged(CELESTE_LIB, snaps, {"Salt": 60})["Salt"]
        self.assertEqual(g, {"app_name": "Salt", "title": "Celeste", "playtimeMinutes": 74,
                             "lastPlayed": "2026-02-26", "cover_url": "https://cdn/Salt.jpg",
                             "store_url": "https://store/Salt"})

    def test_a_library_game_nobody_played_here_keeps_its_cloud_time_and_no_date(self):
        g = self.merged(CELESTE_LIB, {}, {"Salt": 60})["Salt"]
        self.assertEqual((g["playtimeMinutes"], g["lastPlayed"]), (60, None))

    def test_a_game_only_on_another_device_takes_its_card_from_the_snapshot(self):
        snaps = snapshots(laptop={"epic": {"NewGame": {
            "minutes": 45, "title": "New Game", "lastPlayed": "2026-09-27",
            "cover": "https://cdn/new.jpg", "link": "https://store/new"}}})
        g = self.merged({}, snaps, {})["NewGame"]
        self.assertEqual((g["title"], g["cover_url"], g["store_url"], g["playtimeMinutes"]),
                         ("New Game", "https://cdn/new.jpg", "https://store/new", 45))

    def test_a_cloud_record_with_no_title_anywhere_is_dropped(self):
        self.assertEqual(self.merged({}, {}, {"Delisted": 30}), {})


class GogDevices(unittest.TestCase):
    """GOG's cloud already holds every Heroic session, and Heroic pulls that total
    back down into a device's local file — so devices take the max, never the sum."""

    LIB = {"1423049311": {"title": "Cyberpunk 2077", "cover": "https://gog/c.jpg", "link": None}}

    def merged(self, snaps, cloud):
        return {g["app_name"]: g for g in gog.merge_games(
            self.LIB, gd.per_game(snaps, "gog"), cloud)}

    def two_devices(self):
        return snapshots(
            pc={"gog": {"1423049311": {"minutes": 478, "title": "Cyberpunk 2077",
                                       "lastPlayed": "2026-08-01"}}},
            laptop={"gog": {"1423049311": {"minutes": 520, "title": "Cyberpunk 2077",
                                           "lastPlayed": "2026-09-20"}}})

    def test_devices_take_the_max_not_the_sum(self):
        g = self.merged(self.two_devices(), {})["1423049311"]
        self.assertEqual(g["playtimeMinutes"], 520)
        self.assertEqual(g["lastPlayed"], "2026-09-20")

    def test_the_cloud_wins_when_higher(self):
        cloud = {"1423049311": {"minutes": 900, "ach_unlocked": 2, "ach_total": 40}}
        g = self.merged(self.two_devices(), cloud)["1423049311"]
        self.assertEqual((g["playtimeMinutes"], g["ach_unlocked"], g["ach_total"]), (900, 2, 40))

    def test_achievements_are_requested_for_a_game_played_only_elsewhere(self):
        snaps = snapshots(laptop={"gog": {"7": {"minutes": 30, "title": "Laptop Only"}}})
        seen = {}

        def fake_cloud(auth, apps, **kwargs):
            seen.update(apps=set(apps), **kwargs)
            return {}

        with mock.patch.object(gog, "collect_cloud", side_effect=fake_cloud), \
                mock.patch.object(gog.gaming_devices, "read_library", return_value=self.LIB):
            games = quiet(gog.build_games, "heroic", "auth.json", "covers", snapshots=snaps,
                          include_unplayed=False, do_cloud=True, do_achievements=True,
                          do_covers=False)
        self.assertIn("7", seen["apps"])
        self.assertIn("7", seen["played"])
        self.assertTrue(seen["want_achievements"])
        self.assertEqual([g["app_name"] for g in games], ["7"])

    def test_the_cloud_loop_fetches_achievements_for_anything_played_anywhere(self):
        fetched = []

        def fake_get(url, token):
            if "/sessions" in url:
                return {"time_sum": 30 if "/games/8/" in url else 0}
            fetched.append(url.split("/clients/")[1].split("/")[0])
            return {"items": [{"date_unlocked": "2026-01-01"}, {}]}

        with mock.patch.object(gog, "refresh_gog_token",
                               return_value={"access_token": "a", "user_id": "u"}), \
                mock.patch.object(gog, "_gameplay_get", side_effect=fake_get):
            cloud = quiet(gog.collect_cloud, None, {"7", "8", "9"}, want_achievements=True,
                          played={"7"}, refresh_token="r", user_id="u")
        # 7: played on a device; 8: played per the cloud only; 9: never played.
        self.assertEqual(sorted(fetched), ["7", "8"])
        self.assertEqual((cloud["8"]["ach_unlocked"], cloud["8"]["ach_total"]), (1, 2))
        self.assertIsNone(cloud["9"]["ach_total"])


class SharedShape(unittest.TestCase):
    def test_all_three_own_the_same_human_fields(self):
        self.assertEqual(steam.HUMAN_FIELDS, epic.HUMAN_FIELDS)
        self.assertEqual(steam.HUMAN_FIELDS, gog.HUMAN_FIELDS)
        self.assertIn("extraMinutes", steam.HUMAN_FIELDS)


if __name__ == "__main__":
    unittest.main()
