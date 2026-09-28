"""Per-device Heroic snapshots (scripts/gaming_devices.py).

The promise the whole module exists for: the syncs can run on any machine
without overwriting another machine's data. A run writes only its own device's
snapshot, a snapshot holds an allowlist of fields and nothing from the token
files, and it never silently shrinks.

Every test builds a throwaway Heroic config dir; nothing reads the real one and
nothing reaches the network. Design: docs/concepts/gaming-devices.md.
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _load  # noqa: F401
import gaming_devices as gd

SECRET = "sentinel-refresh-token-do-not-export"


def make_heroic(root, *, epic=(), gog=(), played=None, saves=None):
    """A minimal Heroic config dir. `epic` / `gog` are library rows, `played` is
    store/timestamp.json, `saves` gog_store/saveTimestamps.json. Both token files
    are written too, holding SECRET, so a test can prove they stay unread."""
    root = Path(root)
    (root / "store_cache").mkdir(parents=True)
    (root / "store").mkdir()
    (root / "gog_store").mkdir()
    (root / "legendaryConfig" / "legendary").mkdir(parents=True)
    (root / "store_cache" / "legendary_library.json").write_text(
        json.dumps({"library": list(epic)}))
    (root / "store_cache" / "gog_library.json").write_text(json.dumps({"games": list(gog)}))
    (root / "store" / "timestamp.json").write_text(json.dumps(played or {}))
    if saves is not None:
        (root / "gog_store" / "saveTimestamps.json").write_text(json.dumps(saves))
    (root / "legendaryConfig" / "legendary" / "user.json").write_text(
        json.dumps({"refresh_token": SECRET, "account_id": "acc"}))
    (root / "gog_store" / "auth.json").write_text(
        json.dumps({"46899977096215655": {"refresh_token": SECRET, "user_id": "u"}}))
    return root


def epic_row(app, title, **extra):
    row = {"app_name": app, "title": title, "art_square": f"https://cdn/{app}.jpg",
           "store_url": f"https://store/{app}"}
    row.update(extra)
    return row


def gog_row(app, title, **extra):
    row = {"app_name": app, "title": title, "art_square": f"https://gog/{app}.jpg"}
    row.update(extra)
    return row


def ts(minutes, last="", first=""):
    return {"totalPlayed": minutes, "lastPlayed": last, "firstPlayed": first}


# The machine this suite pretends to be.
PC = dict(
    epic=[epic_row("Salt", "Celeste"), epic_row("CrabEA", "Satisfactory"),
          epic_row("Unplayed", "Never Launched")],
    gog=[gog_row("1423049311", "Cyberpunk 2077"),
         gog_row("1297352383", "Thronebreaker"),
         gog_row("999", "Some DLC", install={"is_dlc": True}),
         gog_row("gog-redist", "Redistributables")],
    played={
        "Salt": ts(14, "2026-02-26T10:00:00.000Z", "2025-11-01T09:00:00.000Z"),
        "CrabEA": ts(9, "2026-08-01T22:31:47.190Z"),
        "1423049311": ts(478, "2026-08-01T22:31:47.190Z"),
        "1297352383": ts(28),                       # a total with no date at all
        "999": ts(60, "2026-01-01T00:00:00.000Z"),  # DLC — not a game
        "amzn1.adg.product.x": ts(5, "2026-01-01T00:00:00.000Z"),  # Amazon — no store here
    },
    # 2026-08-01 12:00:00 UTC — the date fallback for the dateless GOG total.
    saves={"1297352383": {"saves": "1785585600"}},
)


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devices = self.tmp / "devices"
        self.addCleanup(self._tmp.cleanup)

    def heroic(self, name="pc", **spec):
        return make_heroic(self.tmp / f"heroic-{name}", **(spec or PC))


class Export(Base):
    def test_only_played_games_of_the_two_stores(self):
        stores = gd.read_local(self.heroic())
        self.assertEqual(sorted(stores["epic"]), ["CrabEA", "Salt"])
        # DLC, redistributables and Amazon titles are not in the snapshot.
        self.assertEqual(sorted(stores["gog"]), ["1297352383", "1423049311"])

    def test_the_fields_are_the_allowlist_and_dates_are_dates(self):
        snap, _ = gd.export("pc", self.heroic(), self.devices, write=True)
        self.assertEqual(set(snap), set(gd.SNAPSHOT_FIELDS))
        for store in gd.STORES:
            for rec in snap["stores"][store].values():
                self.assertLessEqual(set(rec), set(gd.GAME_FIELDS))
                if "lastPlayed" in rec:
                    self.assertRegex(rec["lastPlayed"], r"^\d{4}-\d{2}-\d{2}$")
        salt = snap["stores"]["epic"]["Salt"]
        self.assertEqual(salt, {"cover": "https://cdn/Salt.jpg", "lastPlayed": "2026-02-26",
                                "link": "https://store/Salt", "minutes": 14,
                                "title": "Celeste"})
        # firstPlayed and clock times never leave the machine.
        text = (self.devices / "pc.json").read_text()
        self.assertNotIn("firstPlayed", text)
        self.assertNotIn("T10:00", text)

    def test_gog_takes_the_cloud_save_date_when_heroic_recorded_none(self):
        stores = gd.read_local(self.heroic())
        self.assertEqual(stores["gog"]["1297352383"]["lastPlayed"], "2026-08-01")
        self.assertEqual(stores["gog"]["1297352383"]["minutes"], 28)

    def test_gog_links_are_never_set(self):
        stores = gd.read_local(self.heroic())
        self.assertNotIn("link", stores["gog"]["1423049311"])

    def test_no_token_file_is_opened_and_nothing_secret_is_written(self):
        heroic = self.heroic()
        opened = []
        real = Path.read_text

        def spy(path, *a, **k):
            opened.append(Path(path).name)
            return real(path, *a, **k)

        with mock.patch.object(Path, "read_text", autospec=True, side_effect=spy):
            gd.export("pc", heroic, self.devices, write=True)
        self.assertNotIn("user.json", opened)
        self.assertNotIn("auth.json", opened)
        text = (self.devices / "pc.json").read_text()
        self.assertNotIn(SECRET, text)
        self.assertNotIn(str(self.tmp), text)  # no paths

    def test_a_second_export_is_byte_identical(self):
        heroic = self.heroic()
        _, first = gd.export("pc", heroic, self.devices, write=True)
        before = (self.devices / "pc.json").read_bytes()
        _, second = gd.export("pc", heroic, self.devices, write=True)
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(before, (self.devices / "pc.json").read_bytes())

    def test_a_dry_run_writes_nothing(self):
        _, changed = gd.export("pc", self.heroic(), self.devices, write=False)
        self.assertTrue(changed)
        self.assertFalse((self.devices / "pc.json").exists())


class OnlyItsOwnFile(Base):
    def test_a_run_never_touches_another_devices_snapshot(self):
        laptop = self.heroic("laptop", epic=[epic_row("Salt", "Celeste")],
                             played={"Salt": ts(300, "2026-09-20T18:00:00.000Z")})
        gd.export("laptop", laptop, self.devices, write=True)
        laptop_bytes = (self.devices / "laptop.json").read_bytes()

        snapshots, _ = gd.collect(self.heroic(), self.devices, "pc", write=True)

        self.assertEqual(laptop_bytes, (self.devices / "laptop.json").read_bytes())
        self.assertEqual(list(snapshots), ["laptop", "pc"])
        self.assertEqual(snapshots["laptop"]["stores"]["epic"]["Salt"]["minutes"], 300)
        self.assertTrue((self.devices / "pc.json").exists())

    def test_the_same_snapshots_whichever_machine_runs_it(self):
        pc = self.heroic()
        laptop = self.heroic("laptop", epic=[epic_row("Salt", "Celeste")],
                             played={"Salt": ts(300, "2026-09-20T18:00:00.000Z")})
        gd.export("laptop", laptop, self.devices, write=True)
        from_pc, _ = gd.collect(pc, self.devices, "pc", write=True)
        from_laptop, _ = gd.collect(laptop, self.devices, "laptop", write=True)
        self.assertEqual(from_pc, from_laptop)

    def test_a_dry_run_merges_the_fresh_export_without_writing_it(self):
        snapshots, changed = gd.collect(self.heroic(), self.devices, "pc", write=False)
        self.assertTrue(changed)
        self.assertIn("pc", snapshots)
        self.assertFalse((self.devices / "pc.json").exists())


class DeviceId(Base):
    def test_no_id_with_played_games_is_an_error(self):
        with self.assertRaises(gd.DeviceError) as ctx:
            gd.collect(self.heroic(), self.devices, None, write=True)
        self.assertIn("GAMING_DEVICE", str(ctx.exception))
        self.assertFalse(self.devices.exists())

    def test_no_id_with_nothing_played_just_merges_the_others(self):
        idle = self.heroic("idle", epic=[epic_row("Salt", "Celeste")], played={})
        snapshots, changed = gd.collect(idle, self.devices, None, write=True)
        self.assertEqual(snapshots, {})
        self.assertFalse(changed)

    def test_the_id_comes_from_the_environment(self):
        with mock.patch.dict(os.environ, {"GAMING_DEVICE": "laptop"}):
            self.assertEqual(gd.resolve_device(None), "laptop")
            self.assertEqual(gd.resolve_device("pc"), "pc")  # the flag wins
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(gd.resolve_device(None))

    def test_bad_ids_are_refused(self):
        for bad in ("Laptop", "my pc", "pc_2", "-pc", "pc--2", "pc-until-2026-09-28"):
            with self.subTest(bad=bad), self.assertRaises(gd.DeviceError):
                gd.check_device(bad)
        for good in ("pc", "laptop", "steam-deck", "pc2"):
            gd.check_device(good)


class NeverShrinks(Base):
    def reinstalled(self):
        """The same machine after Heroic was reinstalled: one short session."""
        return self.heroic("fresh", epic=PC["epic"], gog=PC["gog"],
                           played={"Salt": ts(2, "2026-09-28T10:00:00.000Z")})

    def test_a_shrinking_export_is_refused_and_writes_nothing(self):
        gd.export("pc", self.heroic(), self.devices, write=True)
        before = (self.devices / "pc.json").read_bytes()
        with self.assertRaises(gd.DeviceError) as ctx:
            gd.export("pc", self.reinstalled(), self.devices, write=True)
        message = str(ctx.exception)
        self.assertIn("Celeste (Salt): 14 -> 2 min", message)
        self.assertIn("Cyberpunk 2077 (1423049311): 478 min -> gone", message)
        self.assertIn("--rotate", message)
        self.assertEqual(before, (self.devices / "pc.json").read_bytes())

    def test_the_syncs_stop_on_it_too(self):
        gd.export("pc", self.heroic(), self.devices, write=True)
        with self.assertRaises(gd.DeviceError):
            gd.collect(self.reinstalled(), self.devices, "pc", write=False)

    def test_rotate_freezes_the_old_snapshot_and_both_are_merged(self):
        gd.export("pc", self.heroic(), self.devices, write=True)
        frozen = gd.rotate(self.devices, "pc", "2026-09-28")
        self.assertEqual(frozen.name, "pc-until-2026-09-28.json")
        gd.export("pc", self.reinstalled(), self.devices, write=True)

        snapshots = gd.load_snapshots(self.devices)
        self.assertEqual(list(snapshots), ["pc", "pc-until-2026-09-28"])
        self.assertEqual(snapshots["pc-until-2026-09-28"]["device"], "pc-until-2026-09-28")
        self.assertEqual(snapshots["pc-until-2026-09-28"]["stores"]["epic"]["Salt"]["minutes"], 14)
        self.assertEqual(snapshots["pc"]["stores"]["epic"]["Salt"]["minutes"], 2)

    def test_force_overwrites(self):
        gd.export("pc", self.heroic(), self.devices, write=True)
        gd.export("pc", self.reinstalled(), self.devices, write=True, force=True)
        snap = gd.load_snapshot(self.devices / "pc.json")
        self.assertEqual(snap["stores"]["epic"]["Salt"]["minutes"], 2)

    def test_a_date_only_record_may_vanish(self):
        gd.export("pc", self.heroic(gog=[gog_row("7", "Save Only")], played={},
                                    saves={"7": {"saves": "1785585600"}}),
                  self.devices, write=True)
        gd.export("pc", self.heroic("later", gog=[gog_row("7", "Save Only")], played={}),
                  self.devices, write=True)
        self.assertEqual(gd.load_snapshot(self.devices / "pc.json")["stores"]["gog"], {})

    def test_growth_is_fine(self):
        gd.export("pc", self.heroic(), self.devices, write=True)
        grown = dict(PC, played=dict(PC["played"], Salt=ts(20, "2026-09-28T10:00:00.000Z")))
        _, changed = gd.export("pc", self.heroic("grown", **grown), self.devices, write=True)
        self.assertTrue(changed)


class Validation(Base):
    def write(self, name, data):
        self.devices.mkdir(exist_ok=True)
        (self.devices / f"{name}.json").write_text(json.dumps(data))

    def good(self, device="laptop"):
        return {"schema": 1, "device": device, "stores": {
            "epic": {"Salt": {"minutes": 3, "title": "Celeste"}}, "gog": {}}}

    def test_a_good_snapshot_loads(self):
        self.write("laptop", self.good())
        self.assertIn("laptop", gd.load_snapshots(self.devices))

    def test_refused(self):
        cases = {
            "device mismatch": self.good("pc"),
            "extra top-level key": dict(self.good(), host="gaming-rig"),
            "unknown store": dict(self.good(), stores={"amazon": {}}),
            "extra game key": dict(self.good(), stores={"epic": {"Salt": {
                "minutes": 3, "title": "Celeste", "installPath": "/home/x"}}}),
            "negative minutes": dict(self.good(), stores={"epic": {"Salt": {
                "minutes": -1, "title": "Celeste"}}}),
            "clock time": dict(self.good(), stores={"epic": {"Salt": {
                "minutes": 3, "title": "Celeste", "lastPlayed": "2026-01-01T10:00:00Z"}}}),
            "unknown schema": dict(self.good(), schema=2),
        }
        for label, data in cases.items():
            with self.subTest(label):
                self.write("laptop", data)
                with self.assertRaises(gd.DeviceError):
                    gd.load_snapshots(self.devices)


class Helpers(unittest.TestCase):
    def snaps(self, **by_device):
        return {d: {"schema": 1, "device": d, "stores": {"epic": games, "gog": {}}}
                for d, games in by_device.items()}

    def test_newest(self):
        self.assertEqual(gd.newest(["2026-01-02", None, "2026-03-01", ""]), "2026-03-01")
        self.assertIsNone(gd.newest([None, ""]))

    def test_per_game_keeps_device_order(self):
        snaps = self.snaps(laptop={"Salt": {"minutes": 1, "title": "C"}},
                           pc={"Salt": {"minutes": 2, "title": "C"}})
        self.assertEqual([d for d, _ in gd.per_game(snaps, "epic")["Salt"]], ["laptop", "pc"])

    def test_a_copied_heroic_config_is_flagged(self):
        same = {"minutes": 14, "title": "Celeste", "lastPlayed": "2026-02-26"}
        snaps = self.snaps(pc={"Salt": same}, laptop={"Salt": dict(same)})
        self.assertEqual(gd.copied_config_suspects(snaps, "epic"), [("Salt", ["pc", "laptop"])])

    def test_two_real_devices_are_not_flagged(self):
        snaps = self.snaps(pc={"Salt": {"minutes": 14, "title": "C", "lastPlayed": "2026-02-26"}},
                           laptop={"Salt": {"minutes": 14, "title": "C", "lastPlayed": "2026-09-20"}})
        self.assertEqual(gd.copied_config_suspects(snaps, "epic"), [])

    def test_status_has_one_line_per_device(self):
        snaps = self.snaps(laptop={"Salt": {"minutes": 300, "title": "C", "lastPlayed": "2026-09-20"}},
                           pc={})
        lines = gd.status_lines(snaps)
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[1].startswith("laptop"))
        self.assertIn("300", lines[1])
        self.assertIn("2026-09-20", lines[1])


class Cli(Base):
    def run_cli(self, *args):
        err, out = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=False) as env, \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            env.pop("GAMING_DEVICE", None)
            rc = gd.main([*args, "--devices-dir", str(self.devices),
                          "--env-file", str(self.tmp / "no.env")])
        return rc, out.getvalue(), err.getvalue()

    def test_export_status_check(self):
        heroic = str(self.heroic())
        rc, _, err = self.run_cli("export", "--device", "pc", "--heroic-config", heroic)
        self.assertEqual(rc, 0, err)
        self.assertTrue((self.devices / "pc.json").exists())

        rc, out, _ = self.run_cli("status")
        self.assertEqual(rc, 0)
        self.assertIn("pc", out)

        rc, _, err = self.run_cli("check", "--device", "pc", "--heroic-config", heroic)
        self.assertEqual(rc, 0, err)
        self.assertIn("pc.json unchanged", err)

    def test_check_without_a_device_id_fails_and_writes_nothing(self):
        rc, _, err = self.run_cli("check", "--heroic-config", str(self.heroic()))
        self.assertEqual(rc, 1)
        self.assertIn("GAMING_DEVICE", err)
        self.assertFalse(self.devices.exists())

    def test_export_rotate(self):
        heroic = str(self.heroic())
        self.run_cli("export", "--device", "pc", "--heroic-config", heroic)
        rc, _, err = self.run_cli("export", "--device", "pc", "--rotate", "--heroic-config", heroic)
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(list(self.devices.glob("pc-until-*.json"))), 1)
        self.assertTrue((self.devices / "pc.json").exists())


if __name__ == "__main__":
    unittest.main()
