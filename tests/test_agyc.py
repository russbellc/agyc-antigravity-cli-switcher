"""
Automated unit test suite for `lib/agyc_core.py`.

All tests run hermetically inside `tempfile.TemporaryDirectory` with zero network I/O
and complete in well under 1 second.
"""

from __future__ import annotations

import json
import os
import socket
import stat
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib import agyc_core  # noqa: E402
from lib import platform as agyc_platform  # noqa: E402


class AgycCoreIsolatedTestCase(unittest.TestCase):
    """Base test case isolating HOME / AGYC_REAL_HOME inside a temporary directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = self._tmp.name
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "AGYC_REAL_HOME": self.tmp_dir,
                "REAL_HOME": self.tmp_dir,
                "HOME": self.tmp_dir,
            },
            clear=False,
        )
        self._env_patch.start()
        for k in ("ANTIGRAVITY_HOME", "AGY_CONFIG_DIR", "AGYC_CACHE_DIR", "HERDR_SOCKET_PATH", "HERDR_PANE_ID"):
            os.environ.pop(k, None)

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmp.cleanup()


class TestPathsAliasesAndSecurity(AgycCoreIsolatedTestCase):
    def test_01_normalize_and_validate_alias_valid_cases(self) -> None:
        self.assertEqual(agyc_core.normalize_alias("agy1"), "agy01")
        self.assertEqual(agyc_core.normalize_alias("agy2"), "agy02")
        self.assertEqual(agyc_core.normalize_alias("agi5"), "agy05")
        self.assertEqual(agyc_core.normalize_alias("AGY10"), "agy10")
        self.assertEqual(agyc_core.validate_alias("agy2"), "agy02")
        self.assertEqual(agyc_core.validate_alias("work_01"), "work_01")
        self.assertEqual(agyc_core.validate_alias("team-dev"), "team-dev")

    def test_02_validate_alias_rejects_traversal_reserved_and_empty(self) -> None:
        invalid_samples = [
            "",
            "   ",
            "../x",
            "../../etc/passwd",
            "agy01/evil",
            "agy01\\evil",
            ".hidden",
            "-flag",
            "config",
            "CONFIG",
            "agyc",
            "agy",
            "agi",
            "agy-real",
            "agyc-statusline",
            "auto",
            "wipe",
            "a" * 33,
        ]
        for bad in invalid_samples:
            with self.subTest(alias=bad):
                with self.assertRaises(ValueError):
                    agyc_core.validate_alias(bad)

    def test_03_resolve_real_home_ignores_isolated_agyc_homes(self) -> None:
        fake_real = os.path.join(self.tmp_dir, "real_user")
        os.makedirs(fake_real, mode=0o700)
        iso_home = os.path.join(fake_real, ".agyc_homes", "agy10")
        os.makedirs(iso_home, mode=0o700)

        # Separator-agnostic .agyc_homes detection/stripping (both '/' and '\\')
        self.assertTrue(agyc_core._has_agyc_homes_segment(r"C:\Users\dev\.agyc_homes\agy01"))
        self.assertTrue(agyc_core._has_agyc_homes_segment("/home/dev/.agyc_homes"))
        self.assertEqual(agyc_core._strip_agyc_homes(r"C:\Users\dev\.agyc_homes\agy01"), r"C:\Users\dev")
        self.assertEqual(agyc_core._strip_agyc_homes("/home/dev/.agyc_homes/agy01"), "/home/dev")
        self.assertEqual(agyc_core._extract_alias_from_home_path(r"C:\Users\dev\.agyc_homes\agy4"), "agy04")
        self.assertEqual(agyc_core._extract_alias_from_home_path("/home/dev/.agyc_homes/work_01"), "work_01")

        if os.name == "nt":
            with mock.patch.dict(
                os.environ,
                {
                    "AGYC_REAL_HOME": iso_home,
                    "REAL_HOME": iso_home,
                    "HOME": iso_home,
                    "USERPROFILE": iso_home,
                },
                clear=False,
            ):
                self.assertEqual(agyc_core.resolve_real_home(), fake_real)

            with mock.patch.dict(
                os.environ,
                {
                    "AGYC_REAL_HOME": "",
                    "REAL_HOME": "",
                    "HOME": iso_home,
                    "USERPROFILE": iso_home,
                },
                clear=False,
            ):
                self.assertEqual(agyc_core.resolve_real_home(), fake_real)
        else:
            fake_pw = mock.Mock()
            fake_pw.pw_dir = os.path.join(fake_real, ".agyc_homes", "agy10")

            with mock.patch.dict(
                os.environ,
                {
                    "AGYC_REAL_HOME": iso_home,
                    "REAL_HOME": iso_home,
                    "HOME": iso_home,
                },
                clear=False,
            ), mock.patch("pwd.getpwuid", return_value=fake_pw):
                self.assertEqual(agyc_core.resolve_real_home(), fake_real)

    def test_04_private_directories_enforce_0700_permissions(self) -> None:
        acc_dir = agyc_core.get_accounts_dir(self.tmp_dir)
        cache_dir = agyc_core.get_cache_dir(self.tmp_dir)
        locks_dir = agyc_core.get_locks_dir(self.tmp_dir)
        run_dir = agyc_core.get_run_dir(self.tmp_dir)

        tmp_abs = os.path.abspath(self.tmp_dir)
        for d in (acc_dir, cache_dir, locks_dir, run_dir):
            self.assertTrue(os.path.isdir(d), f"Missing directory: {d}")
            self.assertEqual(os.path.commonpath([tmp_abs, os.path.abspath(d)]), tmp_abs)
            probe = os.path.join(d, ".probe")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.unlink(probe)
            if os.name != "nt":
                mode = stat.S_IMODE(os.stat(d).st_mode)
                self.assertEqual(mode, 0o700, f"Expected 0700 on {d}, got {oct(mode)}")

    def test_05_atomic_write_json_enforces_0600_and_valid_payload(self) -> None:
        target = os.path.join(self.tmp_dir, "nested", "secret_account.json")
        payload = {"alias": "agy02", "email": "dev1@gmail.com", "locked": False}
        agyc_core.atomic_write_json(target, payload, mode=0o600, indent=2)

        self.assertTrue(os.path.isfile(target))
        if os.name != "nt":
            file_mode = stat.S_IMODE(os.stat(target).st_mode)
            self.assertEqual(file_mode, 0o600)
        with open(target, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded, payload)

        updated = {"alias": "agy02", "email": "dev1@gmail.com", "locked": True}
        agyc_core.atomic_write_json(target, updated, mode=0o600, indent=2)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), updated)
        leftovers = [fn for fn in os.listdir(os.path.dirname(target)) if ".tmp." in fn]
        self.assertEqual(leftovers, [])

    def test_06_sanitize_account_for_json_strips_all_secrets_and_keeps_active_panes(self) -> None:
        future_rst = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
        raw_account = {
            "alias": "agy2",
            "email": "pro2@example.com",
            "name": "Dev Two",
            "access_token": "ya29.TOP_LEVEL_LEAK",
            "refresh_token": "1//0TOP_LEVEL_REFRESH_LEAK",
            "id_token": "eyJhbGciOiJSUzI1NiJ9.TOP_LEVEL_JWT",
            "client_secret": "GOCSPX-SECRET-LEAK",
            "token_data": {
                "token": {
                    "access_token": "ya29.SECRET_ACCESS_TOKEN",
                    "refresh_token": "1//0SECRET_REFRESH_TOKEN",
                    "token_type": "Bearer",
                },
                "id_token": "eyJhbGciOiJSUzI1NiJ9.NESTED_JWT",
            },
            "quota": {
                "plan_type": "PRO",
                "tier_id": "g1-pro-tier",
                "tier_name": "Google AI Pro",
                "supports_carbon": False,
                "gemini_5h_fraction": 0.84,
                "gemini_5h_reset": future_rst,
                "gemini_weekly_fraction": 0.92,
                "gemini_weekly_reset": future_rst,
                "access_token": "ya29.QUOTA_INJECTED_SECRET",
            },
            "locked": False,
            "note": "ok",
        }

        sanitized = agyc_core.sanitize_account_for_json(
            "agy2",
            raw_account,
            active_account="agy02",
            default_account="agy01",
            active_panes=["w3:p2", "w3:p3Q"],
        )
        serialized = json.dumps(sanitized)

        for forbidden in (
            "token_data",
            "access_token",
            "refresh_token",
            "id_token",
            "client_secret",
            "ya29.",
            "1//0",
            "eyJhbGci",
            "GOCSPX",
        ):
            self.assertNotIn(forbidden, serialized)

        self.assertEqual(sanitized["alias"], "agy02")
        self.assertTrue(sanitized["is_active"])
        self.assertFalse(sanitized["is_default"])
        self.assertEqual(sanitized["active_panes"], ["w3:p2", "w3:p3Q"])
        self.assertEqual(sanitized["plan_type"], "PRO")


class TestWindowsDisplayAndContext(AgycCoreIsolatedTestCase):
    def test_07_normalize_window_recharges_expired_reset_to_100_percent(self) -> None:
        now_dt = datetime(2026, 11, 18, 12, 0, 0, tzinfo=timezone.utc)
        past_str = "2026-11-18T11:59:59Z"
        exact_now_str = "2026-11-18T12:00:00.000000000Z"

        self.assertEqual(agyc_core.normalize_window(0.0, past_str, now_dt=now_dt), (1.0, None))
        self.assertEqual(agyc_core.normalize_window(0.35, exact_now_str, now_dt=now_dt), (1.0, None))

    def test_08_normalize_window_clears_synthetic_reset_above_09995_and_keeps_0996(self) -> None:
        now_dt = datetime(2026, 11, 18, 12, 0, 0, tzinfo=timezone.utc)
        future_str = "2026-11-18T16:30:00Z"

        self.assertEqual(agyc_core.normalize_window(0.9999, future_str, now_dt=now_dt), (1.0, None))
        self.assertEqual(agyc_core.normalize_window(0.996, future_str, now_dt=now_dt), (0.996, future_str))

    def test_09_pct_display_uses_strict_floor_without_false_100(self) -> None:
        self.assertEqual(agyc_core.pct_display(None), 100)
        self.assertEqual(agyc_core.pct_display(1.0), 100)
        self.assertEqual(agyc_core.pct_display(0.9999), 100)
        self.assertEqual(agyc_core.pct_display(0.996), 99)
        self.assertEqual(agyc_core.pct_display(0.72), 72)
        self.assertEqual(agyc_core.pct_display(0.29), 29)
        self.assertEqual(agyc_core.pct_display(0.0005), 0)
        self.assertEqual(agyc_core.pct_display(0.0), 0)

    def test_10_default_max_tokens_for_model_families(self) -> None:
        self.assertEqual(agyc_core.default_max_tokens_for_model("GPT-OSS 120B"), 131_072)
        self.assertEqual(agyc_core.default_max_tokens_for_model("gpt-oss-120b-medium"), 131_072)
        self.assertEqual(agyc_core.default_max_tokens_for_model("Claude Opus 5.5"), 250_000)
        self.assertEqual(agyc_core.default_max_tokens_for_model("Claude Sonnet 4.6"), 250_000)
        self.assertEqual(agyc_core.default_max_tokens_for_model("Claude Haiku 4.5"), 200_000)
        self.assertEqual(agyc_core.default_max_tokens_for_model("Gemini 3.8 Flash Image"), 65_536)
        self.assertEqual(agyc_core.default_max_tokens_for_model("Gemini 4 Carbon"), 1_048_576)

    def test_11_estimate_context_simple_conversation_across_model_limits(self) -> None:
        tp = os.path.join(self.tmp_dir, "simple_transcript.jsonl")
        entries = [
            {"type": "USER_INPUT", "content": "Analiza este servicio"},
            {
                "type": "PLANNER_RESPONSE",
                "content": "Listo",
                "usage": {
                    "input_tokens": 50_000,
                    "cache_read_input_tokens": 14_000,
                    "output_tokens": 1_536,
                },
            },
        ]
        with open(tp, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        frac_gpt, used_gpt, max_gpt = agyc_core.estimate_context_from_transcript(
            tp, agyc_core.default_max_tokens_for_model("GPT-OSS 120B")
        )
        self.assertEqual(used_gpt, 65_536)
        self.assertEqual(max_gpt, 131_072)
        self.assertAlmostEqual(frac_gpt, 0.50, places=4)

        frac_claude, used_claude, max_claude = agyc_core.estimate_context_from_transcript(
            tp, agyc_core.default_max_tokens_for_model("Claude Opus 5.5")
        )
        self.assertEqual(used_claude, 65_536)
        self.assertEqual(max_claude, 250_000)
        self.assertAlmostEqual(frac_claude, 65_536 / 250_000, places=4)

        frac_gem, used_gem, max_gem = agyc_core.estimate_context_from_transcript(
            tp, agyc_core.default_max_tokens_for_model("Gemini 4 Carbon")
        )
        self.assertEqual(used_gem, 65_536)
        self.assertEqual(max_gem, 1_048_576)
        self.assertAlmostEqual(frac_gem, 65_536 / 1_048_576, places=4)

    def test_12_estimate_context_multiple_compactions_ignores_prior_megabytes(self) -> None:
        tp = os.path.join(self.tmp_dir, "multi_compacted.jsonl")
        big_chunk = "A" * 60_000
        with open(tp, "w", encoding="utf-8") as f:
            # ~2.4 MB of pre-compaction history + massive 900k input_tokens before CHECKPOINT #1
            for _ in range(40):
                f.write(json.dumps({"type": "USER_INPUT", "content": big_chunk}) + "\n")
            f.write(
                json.dumps({
                    "type": "PLANNER_RESPONSE",
                    "content": "pre-compaction",
                    "input_tokens": 920_000,
                    "output_tokens": 8_000,
                })
                + "\n"
            )
            f.write(json.dumps({"type": "CHECKPOINT", "content": "Compaction #1 summary"}) + "\n")
            for _ in range(20):
                f.write(json.dumps({"type": "USER_INPUT", "content": big_chunk}) + "\n")
            f.write(json.dumps({"type": "CHECKPOINT", "content": "Compaction #2 summary"}) + "\n")
            # Post-compaction turn with fresh small context
            f.write(json.dumps({"type": "USER_INPUT", "content": "Continuemos con el paso 2"}) + "\n")
            f.write(
                json.dumps({
                    "type": "PLANNER_RESPONSE",
                    "content": "Continuando tras compactar",
                    "input_tokens": 22_000,
                    "output_tokens": 500,
                })
                + "\n"
            )

        frac, used, max_t = agyc_core.estimate_context_from_transcript(tp, 1_048_576)
        self.assertEqual(max_t, 1_048_576)
        self.assertEqual(used, 22_500)
        self.assertLess(frac, 0.03)

    def test_13_estimate_context_freshly_compacted_without_new_planner_response(self) -> None:
        tp = os.path.join(self.tmp_dir, "just_compacted.jsonl")
        summary_text = "# Resuming from a compaction\n" + ("Resumen compacto. " * 200)
        with open(tp, "w", encoding="utf-8") as f:
            f.write(
                json.dumps({
                    "type": "PLANNER_RESPONSE",
                    "content": "huge turn before compact",
                    "input_tokens": 950_000,
                    "output_tokens": 10_000,
                })
                + "\n"
            )
            f.write(json.dumps({"type": "CONTEXT_SUMMARY", "content": summary_text}) + "\n")
            f.write(json.dumps({"type": "USER_INPUT", "content": "Siguiente tarea" * 20}) + "\n")

        frac, used, _ = agyc_core.estimate_context_from_transcript(tp, 1_048_576)
        # Must NOT pick up the 950k pre-compaction input_tokens!
        self.assertGreaterEqual(used, 16_000)
        self.assertLess(used, 25_000)
        self.assertLess(frac, 0.03)


class TestSmartAutoChoiceEngine(AgycCoreIsolatedTestCase):
    def _acc(
        self,
        plan: str = "PRO",
        g5: float = 1.0,
        gw: float = 1.0,
        c5: float = 1.0,
        cw: float = 1.0,
        g5_rst: str | None = None,
        gw_rst: str | None = None,
        locked: bool = False,
        is_revoked: bool = False,
        note: str = "",
    ) -> dict:
        is_ultra = plan.upper() == "ULTRA"
        return {
            "email": f"{plan.lower()}@example.com",
            "plan_type": plan.upper(),
            "locked": locked,
            "is_revoked": is_revoked,
            "note": note,
            "quota": {
                "plan_type": plan.upper(),
                "tier_id": "g1-ultra-tier" if is_ultra else "g1-pro-tier",
                "supports_carbon": is_ultra,
                "gemini_5h_fraction": g5,
                "gemini_5h_reset": g5_rst,
                "gemini_weekly_fraction": gw,
                "gemini_weekly_reset": gw_rst,
                "claude_5h_fraction": c5,
                "claude_weekly_fraction": cw,
            },
        }

    def test_14_skips_locked_and_revoked_accounts(self) -> None:
        accounts = {
            "agy01": self._acc("PRO", g5=1.0, gw=1.0, is_revoked=True),
            "agy07": self._acc("PRO", g5=1.0, gw=1.0, locked=True, note="Fija en p39"),
            "agy04": self._acc("PRO", g5=0.65, gw=0.80),
        }
        res = agyc_core.compute_smart_auto_choice(accounts, "gemini")
        self.assertEqual(res["best_alias"], "agy04")
        by_alias = {e["alias"]: e for e in res["evaluations"]}
        self.assertEqual(by_alias["agy01"]["status"], "revoked")
        self.assertEqual(by_alias["agy07"]["status"], "locked")

    def test_15_strict_and_rule_rejects_5h_zero_with_90_weekly_and_tracks_earliest_reset(self) -> None:
        now_dt = datetime.now(timezone.utc)
        rst_soon = (now_dt + timedelta(minutes=25)).isoformat()
        rst_later = (now_dt + timedelta(hours=3)).isoformat()
        rst_week = (now_dt + timedelta(days=4)).isoformat()

        accounts = {
            # 5H=0%, Sem=90% -> MUST NOT be chosen as available; earliest reset uses 5h_reset (25m)
            "agy02": self._acc("PRO", g5=0.0, gw=0.90, g5_rst=rst_soon, gw_rst=rst_week),
            # 5H=0%, Sem=0% -> blocked on weekly_reset (4d), NOT 5h_reset (10m)
            "agy03": self._acc(
                "PRO",
                g5=0.0,
                gw=0.0,
                g5_rst=(now_dt + timedelta(minutes=10)).isoformat(),
                gw_rst=rst_week,
            ),
            "agy04": self._acc("PRO", g5=0.0, gw=0.85, g5_rst=rst_later, gw_rst=rst_week),
        }
        res = agyc_core.compute_smart_auto_choice(accounts, "gemini")
        self.assertIsNone(res["best_alias"])
        self.assertEqual(res["reason"], "quota_exhausted")
        self.assertEqual(res["earliest_alias"], "agy02")
        self.assertIsNotNone(res["min_reset_seconds"])
        self.assertLessEqual(res["min_reset_seconds"], 25 * 60 + 5)
        self.assertGreater(res["min_reset_seconds"], 20 * 60)

    def test_16_carbon_mode_and_active_carbon_model_select_only_ultra(self) -> None:
        accounts = {
            "agy01": self._acc("PRO", g5=1.0, gw=1.0),
            "agy02": self._acc("PRO", g5=1.0, gw=1.0),
            "agy10": self._acc("ULTRA", g5=0.55, gw=0.75),
        }
        res_explicit = agyc_core.compute_smart_auto_choice(accounts, "carbon")
        self.assertEqual(res_explicit["target_mode"], "carbon")
        self.assertEqual(res_explicit["best_alias"], "agy10")

        res_by_model = agyc_core.compute_smart_auto_choice(
            accounts, "gemini", active_model="Gemini 4 Carbon"
        )
        self.assertEqual(res_by_model["target_mode"], "carbon")
        self.assertEqual(res_by_model["best_alias"], "agy10")

    def test_17_carbon_mode_without_ultra_returns_no_ultra_reason(self) -> None:
        accounts = {
            "agy01": self._acc("PRO", g5=1.0, gw=1.0),
            "agy02": self._acc("PRO", g5=0.9, gw=0.9),
        }
        res = agyc_core.compute_smart_auto_choice(accounts, "carbon")
        self.assertIsNone(res["best_alias"])
        self.assertEqual(res["reason"], "no_ultra")

    def test_18_ultra_reserve_protects_ultra_when_healthy_pro_exists(self) -> None:
        accounts = {
            "agy02": self._acc("PRO", g5=0.80, gw=0.80, c5=0.80, cw=0.80),
            "agy09": self._acc("ULTRA", g5=1.00, gw=1.00, c5=1.00, cw=1.00),
        }
        for mode in ("gemini", "claude"):
            with self.subTest(mode=mode):
                res = agyc_core.compute_smart_auto_choice(accounts, mode)
                self.assertEqual(res["best_alias"], "agy02")
                self.assertEqual(res["ultra_reserved_count"], 1)
                ev_ultra = next(e for e in res["evaluations"] if e["alias"] == "agy09")
                self.assertTrue(ev_ultra["ultra_reserved"])
                self.assertIn("Reserva ULTRA", ev_ultra["reason"])

    def test_19_ultra_reserve_falls_back_to_ultra_when_all_pro_exhausted_or_below_15_pct(self) -> None:
        accounts_zero = {
            "agy02": self._acc("PRO", g5=0.0, gw=0.80),
            "agy09": self._acc("ULTRA", g5=1.0, gw=1.0),
        }
        res_zero = agyc_core.compute_smart_auto_choice(accounts_zero, "gemini")
        self.assertEqual(res_zero["best_alias"], "agy09")
        self.assertEqual(res_zero["ultra_reserved_count"], 0)

        accounts_low = {
            "agy02": self._acc("PRO", g5=0.10, gw=0.80),
            "agy09": self._acc("ULTRA", g5=0.95, gw=0.95),
        }
        res_low = agyc_core.compute_smart_auto_choice(accounts_low, "gemini")
        self.assertEqual(res_low["best_alias"], "agy09")
        self.assertEqual(res_low["ultra_reserved_count"], 0)

    def test_20_anti_collision_prefers_free_account_over_busy_pane_account(self) -> None:
        accounts = {
            "agy02": self._acc("PRO", g5=0.95, gw=0.95),
            "agy03": self._acc("PRO", g5=0.85, gw=0.85),
        }
        active_panes = {
            "agy02": [{"pane_id": "w3:p2", "short_pane": "p2", "label": "Principal", "focused": True}],
        }
        res = agyc_core.compute_smart_auto_choice(
            accounts, "gemini", active_panes_map=active_panes
        )
        self.assertEqual(res["best_alias"], "agy03")

    def test_21_exclude_pane_id_ignores_calling_pane_own_session(self) -> None:
        accounts = {
            "agy02": self._acc("PRO", g5=0.92, gw=0.95),
            "agy03": self._acc("PRO", g5=0.40, gw=0.50),
        }
        active_panes = {
            "agy02": [{"pane_id": "w3:p2", "short_pane": "p2", "label": "Principal", "focused": True}],
        }
        res = agyc_core.compute_smart_auto_choice(
            accounts,
            "gemini",
            active_panes_map=active_panes,
            exclude_pane_id="w3:p2",
        )
        self.assertEqual(res["best_alias"], "agy02")
        ev02 = next(e for e in res["evaluations"] if e["alias"] == "agy02")
        self.assertEqual(ev02["busy_panes"], [])

    def test_22_burn_first_prefers_open_5h_window_over_untouched_100_percent_account(self) -> None:
        future_5h = (datetime.now(timezone.utc) + timedelta(hours=2, minutes=15)).isoformat()
        future_wk = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        accounts = {
            "agy02": self._acc("PRO", g5=1.00, gw=1.00, c5=1.00, cw=1.00),
            "agy03": self._acc(
                "PRO",
                g5=0.72,
                gw=0.95,
                c5=0.72,
                cw=0.95,
                g5_rst=future_5h,
                gw_rst=future_wk,
            ),
        }
        for mode in ("gemini", "claude"):
            with self.subTest(mode=mode):
                res = agyc_core.compute_smart_auto_choice(accounts, mode)
                self.assertEqual(res["best_alias"], "agy03")
                ev03 = next(e for e in res["evaluations"] if e["alias"] == "agy03")
                self.assertTrue(ev03["burn_first"])


class TestHerdrActivePaneScanner(AgycCoreIsolatedTestCase):
    def _create_fake_proc(
        self,
        proc_root: str,
        pid: int,
        comm: str,
        environ_map: dict[str, str],
        state: str = "S",
    ) -> None:
        pdir = os.path.join(proc_root, str(pid))
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "comm"), "wb") as f:
            f.write((comm + "\n").encode("utf-8"))
        with open(os.path.join(pdir, "stat"), "wb") as f:
            f.write(f"{pid} ({comm}) {state} 1 1 1 0\n".encode("utf-8"))
        env_bytes = b"\x00".join(f"{k}={v}".encode("utf-8") for k, v in environ_map.items()) + b"\x00"
        with open(os.path.join(pdir, "environ"), "wb") as f:
            f.write(env_bytes)

    def test_23_scan_active_herdr_panes_enriches_deduplicates_and_discards_dead_panes(self) -> None:
        sock_path = os.path.join(self.tmp_dir, "herdr.sock")
        herdr_response = {
            "id": "1",
            "result": {
                "panes": [
                    {"pane_id": "w3:p2", "label": "Principal", "tab_id": "w3:t1", "focused": True},
                    {"pane_id": "w3:p5", "label": "Soporte", "tab_id": "w3:t1", "focused": False},
                    # Dead pane in Herdr where agy-real is no longer running -> discarded
                    {"pane_id": "w3:pDead", "label": "Viejo", "tab_id": "w3:t2", "focused": False, "agent": "agy"},
                ]
            },
        }

        if os.name == "nt":
            run_dir = agyc_core.get_run_dir(self.tmp_dir)
            for pid, meta in (
                (1001, {"pid": 1001, "home": f"{self.tmp_dir}\\.agyc_homes\\agy10", "herdr_pane_id": "w3:p2"}),
                (1002, {"pid": 1002, "home": f"{self.tmp_dir}\\.agyc_homes\\agy10", "herdr_pane_id": "w3:p2"}),
                (2002, {"pid": 2002, "home": f"{self.tmp_dir}\\.agyc_homes\\agy4", "herdr_pane_id": "w3:p5"}),
                (4001, {"pid": 4001, "home": f"{self.tmp_dir}\\.agyc_homes\\agy06", "herdr_pane_id": "w3:pClosed"}),
                (999999, {"pid": 999999, "home": f"{self.tmp_dir}\\.agyc_homes\\agy08", "herdr_pane_id": "w3:p9"}),
            ):
                with open(os.path.join(run_dir, f"{pid}.json"), "w", encoding="utf-8") as mf:
                    json.dump(meta, mf)

            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port = srv.getsockname()[1]
            with open(sock_path, "w", encoding="utf-8") as sf:
                sf.write(f"{port}:pane_test_id\n")

            def _serve_once() -> None:
                try:
                    conn, _ = srv.accept()
                    with conn:
                        conn.recv(4096)
                        conn.sendall((json.dumps(herdr_response) + "\n").encode("utf-8"))
                finally:
                    srv.close()

            t = threading.Thread(target=_serve_once, daemon=True)
            t.start()

            fake_procs = {
                1001: "agy-real.exe",
                1002: "agy-real.exe",
                2002: "agy-real.exe",
                4001: "agy-real.exe",
            }
            with mock.patch("lib.platform.win32._list_win32_processes", return_value=fake_procs):
                active_map = agyc_core.scan_active_herdr_panes(
                    self.tmp_dir,
                    herdr_socket_path=sock_path,
                    run_dir=run_dir,
                )
            t.join(timeout=1.0)
            self.assertFalse(os.path.exists(os.path.join(run_dir, "999999.json")))
        else:
            fake_proc = os.path.join(self.tmp_dir, "proc")
            os.makedirs(fake_proc)

            # Live agy10 in w3:p2 (parent + child subprocess -> must deduplicate to 1 entry)
            self._create_fake_proc(
                fake_proc,
                1001,
                "agy-real",
                {"HOME": f"{self.tmp_dir}/.agyc_homes/agy10", "HERDR_PANE_ID": "w3:p2"},
            )
            self._create_fake_proc(
                fake_proc,
                1002,
                "agy-real",
                {"HOME": f"{self.tmp_dir}/.agyc_homes/agy10", "HERDR_PANE_ID": "w3:p2"},
            )
            # Stopped (Ctrl+Z) agy03 vs running agy04 in same pane w3:p5 -> agy04 wins
            self._create_fake_proc(
                fake_proc,
                2001,
                "agy-real",
                {"HOME": f"{self.tmp_dir}/.agyc_homes/agy03", "HERDR_PANE_ID": "w3:p5"},
                state="T",
            )
            self._create_fake_proc(
                fake_proc,
                2002,
                "agy-real",
                {"HOME": f"{self.tmp_dir}/.agyc_homes/agy4", "HERDR_PANE_ID": "w3:p5"},
                state="S",
            )
            # Zombie process in w3:p9 -> ignored
            self._create_fake_proc(
                fake_proc,
                3001,
                "agy-real",
                {"HOME": f"{self.tmp_dir}/.agyc_homes/agy08", "HERDR_PANE_ID": "w3:p9"},
                state="Z",
            )
            # Orphaned process pointing to closed pane w3:pClosed -> discarded when Herdr is online
            self._create_fake_proc(
                fake_proc,
                4001,
                "agy-real",
                {"HOME": f"{self.tmp_dir}/.agyc_homes/agy06", "HERDR_PANE_ID": "w3:pClosed"},
            )

            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(sock_path)
            srv.listen(1)

            def _serve_once() -> None:
                try:
                    conn, _ = srv.accept()
                    with conn:
                        conn.recv(4096)
                        conn.sendall((json.dumps(herdr_response) + "\n").encode("utf-8"))
                finally:
                    srv.close()

            t = threading.Thread(target=_serve_once, daemon=True)
            t.start()

            active_map = agyc_core.scan_active_herdr_panes(
                self.tmp_dir,
                proc_root=fake_proc,
                herdr_socket_path=sock_path,
            )
            t.join(timeout=1.0)

        self.assertEqual(set(active_map.keys()), {"agy10", "agy04"})
        self.assertEqual(len(active_map["agy10"]), 1)
        self.assertEqual(active_map["agy10"][0]["pane_id"], "w3:p2")
        self.assertEqual(active_map["agy10"][0]["short_pane"], "p2")
        self.assertEqual(active_map["agy10"][0]["label"], "Principal")
        self.assertEqual(active_map["agy10"][0]["tab_id"], "w3:t1")
        self.assertTrue(active_map["agy10"][0]["focused"])

        self.assertEqual(len(active_map["agy04"]), 1)
        self.assertEqual(active_map["agy04"][0]["short_pane"], "p5")
        self.assertEqual(active_map["agy04"][0]["label"], "Soporte")


class TestPlatformAbstractionLayer(AgycCoreIsolatedTestCase):
    def test_24_acquire_file_lock_concurrent_and_nonblocking(self) -> None:
        import subprocess

        lock_path = os.path.join(agyc_core.get_locks_dir(self.tmp_dir), "oauth.lock")
        lock1 = agyc_platform.acquire_file_lock(lock_path, blocking=False)
        try:
            with self.assertRaises(BlockingIOError):
                agyc_platform.acquire_file_lock(lock_path, blocking=False)

            probe_code = (
                "import sys\n"
                "sys.path.insert(0, %r)\n"
                "from lib import platform as p\n"
                "try:\n"
                "    lk = p.acquire_file_lock(%r, blocking=False)\n"
                "    lk.release()\n"
                "    sys.exit(2)\n"
                "except BlockingIOError:\n"
                "    sys.exit(0)\n"
            ) % (REPO_ROOT, lock_path)
            res = subprocess.run([sys.executable, "-S", "-c", probe_code], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
        finally:
            lock1.release()

        # Idempotent second release must not raise
        lock1.release()

        with agyc_platform.acquire_file_lock(lock_path, blocking=True) as lock2:
            self.assertIsNotNone(lock2)
        with agyc_platform.acquire_file_lock(lock_path, blocking=False) as lock3:
            self.assertIsNotNone(lock3)

    def test_25_create_dir_link_and_read_dir_link(self) -> None:
        with tempfile.TemporaryDirectory() as link_td:
            src_dir = os.path.join(link_td, "real target")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "marker.txt"), "w", encoding="utf-8") as f:
                f.write("linked-ok")

            dst_link = os.path.join(link_td, "nested", "dir_link")
            agyc_platform.create_dir_link(src_dir, dst_link)

            self.assertTrue(agyc_platform.is_dir_link(dst_link))
            self.assertFalse(agyc_platform.is_dir_link(src_dir))
            self.assertTrue(os.path.isdir(dst_link))
            with open(os.path.join(dst_link, "marker.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "linked-ok")

            resolved = agyc_platform.read_dir_link(dst_link)
            self.assertEqual(
                os.path.normcase(os.path.abspath(resolved)),
                os.path.normcase(os.path.abspath(src_dir)),
            )

            with self.assertRaises(FileExistsError):
                agyc_platform.create_dir_link(src_dir, dst_link)

    def test_26_create_file_link_and_repeat_call(self) -> None:
        src_file = os.path.join(self.tmp_dir, "src_settings.json")
        dst_file = os.path.join(self.tmp_dir, "sub", "dst_settings.json")
        with open(src_file, "w", encoding="utf-8") as f:
            f.write('{"model": "Gemini 4 Carbon"}')

        agyc_platform.create_file_link(src_file, dst_file)
        self.assertTrue(os.path.isfile(dst_file))
        with open(dst_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"model": "Gemini 4 Carbon"}')

        # Repeating create_file_link on already-linked file must not crash
        agyc_platform.create_file_link(src_file, dst_file)

    def test_27_read_stdin_nonblocking_pipe_and_timeout(self) -> None:
        import subprocess

        # 1. Empty open pipe must return b"" within timeout without hanging
        r_empty, w_empty = os.pipe()
        try:
            data = agyc_platform.read_stdin_nonblocking(0.015, fd=r_empty)
            self.assertEqual(data, b"")
        finally:
            os.close(r_empty)
            os.close(w_empty)

        # 2. Pipe containing payload returns exact bytes
        r_full, w_full = os.pipe()
        try:
            os.write(w_full, b'{"model":"Claude Opus 5.5"}\n')
            os.close(w_full)
            w_full = -1
            data = agyc_platform.read_stdin_nonblocking(0.050, fd=r_full)
            self.assertEqual(data, b'{"model":"Claude Opus 5.5"}\n')
        finally:
            os.close(r_full)
            if w_full != -1:
                os.close(w_full)

        # 3. End-to-end subprocess fd 0 test
        sub_code = (
            "import sys; sys.path.insert(0, %r); "
            "from lib import platform as p; "
            "sys.stdout.buffer.write(p.read_stdin_nonblocking(0.1))"
        ) % (REPO_ROOT,)
        res = subprocess.run(
            [sys.executable, "-S", "-c", sub_code],
            input=b'{"ok":true}',
            capture_output=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout, b'{"ok":true}')

    def test_28_query_herdr_ipc_transport_and_failures(self) -> None:
        sock_path = os.path.join(self.tmp_dir, "ipc_herdr.sock")
        self.assertIsNone(agyc_platform.query_herdr_ipc(sock_path, {"id": "1", "method": "pane.list"}))

        expected = {"id": "1", "result": {"panes": [{"pane_id": "w1:p1", "focused": True}]}}

        if os.name == "nt":
            with open(sock_path, "w", encoding="utf-8") as sf:
                sf.write("not_a_port:abc\n")
            self.assertIsNone(agyc_platform.query_herdr_ipc(sock_path, {"id": "1", "method": "pane.list"}))

            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port = srv.getsockname()[1]
            with open(sock_path, "w", encoding="utf-8") as sf:
                sf.write(f"{port}:nonce123\n")
        else:
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(sock_path)
            srv.listen(1)

        def _serve() -> None:
            try:
                conn, _ = srv.accept()
                with conn:
                    conn.recv(4096)
                    conn.sendall((json.dumps(expected) + "\n").encode("utf-8"))
            finally:
                srv.close()

        t = threading.Thread(target=_serve, daemon=True)
        t.start()
        resp = agyc_platform.query_herdr_ipc(sock_path, {"id": "1", "method": "pane.list", "params": {}}, timeout=0.5)
        t.join(timeout=1.0)
        self.assertEqual(resp, expected)

    def test_29_cache_isolation_and_win32_process_tools(self) -> None:
        if os.name == "nt":
            from lib.platform import win32 as w32

            # Live Toolhelp32 snapshot must include current python process
            live = w32._list_win32_processes()
            self.assertIn(os.getpid(), live)

            # AGYC_REAL_HOME pointing to tmp_dir isolates cache from real LOCALAPPDATA
            cdir = agyc_platform.get_cache_dir()
            self.assertTrue(os.path.normcase(cdir).startswith(os.path.normcase(self.tmp_dir)))

            # Explicit AGYC_CACHE_DIR overrides cache path
            custom_cache = os.path.join(self.tmp_dir, "custom_cache")
            with mock.patch.dict(os.environ, {"AGYC_CACHE_DIR": custom_cache}, clear=False):
                self.assertEqual(os.path.normcase(agyc_platform.get_cache_dir()), os.path.normcase(custom_cache))

            # Un-overridden USERPROFILE + LOCALAPPDATA resolves to %LOCALAPPDATA%\agyc\cache
            fake_up = os.path.join(self.tmp_dir, "win_user")
            fake_la = os.path.join(fake_up, "AppData", "Local")
            os.makedirs(fake_la, exist_ok=True)
            with mock.patch.dict(
                os.environ,
                {
                    "AGYC_REAL_HOME": "",
                    "REAL_HOME": "",
                    "HOME": "",
                    "USERPROFILE": fake_up,
                    "LOCALAPPDATA": fake_la,
                },
                clear=False,
            ):
                self.assertEqual(
                    os.path.normcase(agyc_platform.get_cache_dir()),
                    os.path.normcase(os.path.join(fake_la, "agyc", "cache")),
                )

            # Dead <pid>.json gets cleaned by scan_agy_processes
            run_dir = agyc_platform.get_run_dir(self.tmp_dir)
            dead_file = os.path.join(run_dir, "999998.json")
            with open(dead_file, "w", encoding="utf-8") as df:
                df.write('{"pid": 999998, "herdr_pane_id": "w1:p9"}')
            agyc_platform.scan_agy_processes(run_dir=run_dir)
            self.assertFalse(os.path.exists(dead_file))
        else:
            cdir = agyc_platform.get_cache_dir()
            self.assertEqual(cdir, os.path.join(self.tmp_dir, ".cache", "agyc"))

    def test_30_python_S_lazy_imports_and_stdlib_platform_not_shadowed(self) -> None:
        import subprocess

        code = (
            "import sys; sys.path.insert(0, %r); "
            "from lib import agyc_core, platform as ap; "
            "heavy = {'ctypes', 'subprocess', 'socket', '_socket', 'msvcrt', 'pwd', 'fcntl', 'select', 'json', 'shutil', 'threading'}; "
            "loaded = heavy.intersection(sys.modules.keys()); "
            "assert not loaded, f'Unexpected eager imports: {loaded}'; "
            "print('OK')"
        ) % (REPO_ROOT,)
        res = subprocess.run([sys.executable, "-S", "-c", code], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        self.assertEqual(res.stdout.strip(), "OK")

        # Also verify direct `import agyc_core` (how bin/agyc loads it) does not shadow stdlib `platform`
        lib_dir = os.path.join(REPO_ROOT, "lib")
        code_direct = (
            "import sys; sys.path.insert(0, %r); "
            "import agyc_core; "
            "assert 'platform' not in sys.modules or hasattr(sys.modules['platform'], 'system'); "
            "print('DIRECT_OK')"
        ) % (lib_dir,)
        res2 = subprocess.run([sys.executable, "-S", "-c", code_direct], capture_output=True, text=True)
        self.assertEqual(res2.returncode, 0, res2.stderr + res2.stdout)
        self.assertEqual(res2.stdout.strip(), "DIRECT_OK")

    def test_31_ensure_private_file_harden_acl_spawn_detached_and_toast(self) -> None:
        priv_dir = os.path.join(self.tmp_dir, "priv_box")
        agyc_platform.ensure_private_dir(priv_dir)
        priv_file = os.path.join(priv_dir, "secret.token")
        agyc_platform.ensure_private_file(priv_file)
        self.assertTrue(os.path.isfile(priv_file))

        if os.name == "nt":
            self.assertTrue(agyc_platform.harden_ntfs_acl(priv_dir))
            self.assertTrue(agyc_platform.harden_ntfs_acl(priv_file))
            self.assertFalse(agyc_platform.harden_ntfs_acl(os.path.join(self.tmp_dir, "nonexistent")))
        else:
            self.assertEqual(stat.S_IMODE(os.stat(priv_file).st_mode), 0o600)

        proc = agyc_platform.spawn_detached([sys.executable, "-S", "-c", "pass"])
        self.assertEqual(proc.wait(timeout=5), 0)

        if os.name == "nt":
            from lib.platform import win32 as w32

            fake_herdr = os.path.join(self.tmp_dir, "herdr.exe")
            with open(fake_herdr, "wb") as hf:
                hf.write(b"")
            with mock.patch("lib.platform.win32.spawn_detached") as m_spawn:
                self.assertTrue(w32.send_low_quota_toast("Alert!", "10% left", herdr_bin=fake_herdr))
                m_spawn.assert_called_once()
                cmd_arg = m_spawn.call_args[0][0]
                self.assertEqual(cmd_arg[0], fake_herdr)
                self.assertIn("notification", cmd_arg)

            with mock.patch("shutil.which", side_effect=lambda name: "powershell.exe" if "powershell" in name else None), \
                 mock.patch("lib.platform.win32.spawn_detached") as m_spawn:
                self.assertTrue(w32.send_low_quota_toast("Alert' $x", "Body \"ok\"", herdr_bin=None))
                m_spawn.assert_called_once()
                kwargs = m_spawn.call_args[1]
                self.assertEqual(kwargs["env"]["AGYC_TOAST_TITLE"], "Alert' $x")
                self.assertEqual(kwargs["env"]["AGYC_TOAST_BODY"], 'Body "ok"')

    def test_32_linux_backend_api_parity_and_proc_scanner(self) -> None:
        from lib.platform import linux as lin, win32 as w32

        lin_pub = {k for k in dir(lin) if not k.startswith("_") and callable(getattr(lin, k))}
        win_pub = {k for k in dir(w32) if not k.startswith("_") and callable(getattr(w32, k))}
        self.assertEqual(lin_pub, win_pub)

        fake_proc = os.path.join(self.tmp_dir, "linux_proc")
        os.makedirs(fake_proc)
        for pid, comm, state, env in (
            (101, "agy-real", "S", {"HOME": "/home/u/.agyc_homes/agy10", "HERDR_PANE_ID": "w1:p1"}),
            (102, "agy-real", "Z", {"HOME": "/home/u/.agyc_homes/agy02", "HERDR_PANE_ID": "w1:p2"}),
            (103, "agy-real", "T", {"AGYC_ACCOUNT": "agy3", "HERDR_PANE_ID": "w1:p3"}),
        ):
            pdir = os.path.join(fake_proc, str(pid))
            os.makedirs(pdir)
            with open(os.path.join(pdir, "comm"), "wb") as cf:
                cf.write((comm + "\n").encode("utf-8"))
            with open(os.path.join(pdir, "stat"), "wb") as sf:
                sf.write(f"{pid} ({comm}) {state} 1 1 1 0\n".encode("utf-8"))
            with open(os.path.join(pdir, "environ"), "wb") as ef:
                ef.write(b"\x00".join(f"{k}={v}".encode("utf-8") for k, v in env.items()) + b"\x00")

        with mock.patch("os.getuid", create=True, return_value=0):
            found = lin.scan_agy_processes(proc_root=fake_proc)
        by_pid = {item["pid"]: item for item in found}
        self.assertEqual(set(by_pid.keys()), {101, 103})
        self.assertEqual(by_pid[101]["alias"], "agy10")
        self.assertTrue(by_pid[101]["is_running"])
        self.assertEqual(by_pid[103]["alias"], "agy03")
        self.assertFalse(by_pid[103]["is_running"])


def _load_agyc_cli_module():
    import importlib.machinery
    import importlib.util

    cli_path = os.path.join(REPO_ROOT, "bin", "agyc")
    loader = importlib.machinery.SourceFileLoader("agyc_cli_mod", cli_path)
    spec = importlib.util.spec_from_loader("agyc_cli_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class TestExportAndImport(unittest.TestCase):
    """Hermetic tests for `agyc export` and `agyc import` using only fake emails."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cli = _load_agyc_cli_module()

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root_dir = self._tmp.name
        self.home1 = os.path.join(self.root_dir, "home1")
        self.home2 = os.path.join(self.root_dir, "home2")
        os.makedirs(self.home1, exist_ok=True)
        os.makedirs(self.home2, exist_ok=True)
        self._env_stack: list[mock._patch] = []
        self._switch_home(self.home1)

    def tearDown(self) -> None:
        while self._env_stack:
            self._env_stack.pop().stop()
        self._tmp.cleanup()

    def _switch_home(self, target_home: str) -> None:
        while self._env_stack:
            self._env_stack.pop().stop()
        patch = mock.patch.dict(
            os.environ,
            {
                "AGYC_REAL_HOME": target_home,
                "REAL_HOME": target_home,
                "HOME": target_home,
                "USERPROFILE": target_home,
                "LOCALAPPDATA": os.path.join(target_home, "AppData", "Local"),
                "APPDATA": os.path.join(target_home, "AppData", "Roaming"),
            },
            clear=False,
        )
        patch.start()
        self._env_stack.append(patch)
        for k in ("ANTIGRAVITY_HOME", "AGY_CONFIG_DIR", "AGYC_CACHE_DIR"):
            os.environ.pop(k, None)

    def _seed_account(self, alias: str, email: str, access_token: str) -> dict:
        acc = {
            "alias": alias,
            "email": email,
            "name": f"Dev {alias}",
            "token_data": {
                "token": {
                    "access_token": access_token,
                    "refresh_token": f"refresh_{alias}_{access_token}",
                    "expiry_date": 9999999999000,
                }
            },
            "quota": {"plan_type": "PRO"},
            "is_revoked": False,
        }
        self.cli.save_account(alias, acc, sync_links=False)
        return acc

    def test_33_export_single_and_all_excludes_underscore_and_config(self) -> None:
        import contextlib
        import io
        from types import SimpleNamespace

        self._seed_account("agy01", "dev1@gmail.com", "tok1")
        self._seed_account("agy02", "dev2@gmail.com", "tok2")
        # Archivo interno prefijado con '_' que debe excluirse
        with open(os.path.join(self.cli.get_accounts_dir(), "_internal.json"), "w", encoding="utf-8") as f:
            json.dump({"ignored": True}, f)

        out_single = os.path.join(self.root_dir, "single.json")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.cli.cmd_export(SimpleNamespace(alias="agy01", output=out_single))
        self.assertIn("scp", buf.getvalue().lower())
        with open(out_single, "r", encoding="utf-8") as f:
            b1 = json.load(f)
        self.assertEqual(b1["format"], "agyc-bundle-v1")
        self.assertIn("exported_at", b1)
        self.assertEqual([e["alias"] for e in b1["accounts"]], ["agy01"])
        self.assertEqual(b1["accounts"][0]["account_data"]["email"], "dev1@gmail.com")

        # Exportar todas usando nombre por defecto en directorio temporal
        cwd_dir = os.path.join(self.root_dir, "cwd_export")
        os.makedirs(cwd_dir, exist_ok=True)
        prev_cwd = os.getcwd()
        try:
            os.chdir(cwd_dir)
            with contextlib.redirect_stdout(io.StringIO()):
                self.cli.cmd_export(SimpleNamespace(alias=None, output=None))
        finally:
            os.chdir(prev_cwd)

        default_bundle = os.path.join(cwd_dir, "agyc-accounts-bundle.json")
        self.assertTrue(os.path.isfile(default_bundle))
        with open(default_bundle, "r", encoding="utf-8") as f:
            b_all = json.load(f)
        self.assertEqual([e["alias"] for e in b_all["accounts"]], ["agy01", "agy02"])

    def test_34_import_into_clean_home_sets_active_and_isolated_home(self) -> None:
        import contextlib
        import io
        from types import SimpleNamespace

        self._seed_account("agy01", "dev1@gmail.com", "tok1")
        self._seed_account("agy02", "dev2@gmail.com", "tok2")
        bundle_path = os.path.join(self.root_dir, "bundle_all.json")
        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.cmd_export(SimpleNamespace(alias=None, output=bundle_path))

        # Cambiar a un HOME limpio
        self._switch_home(self.home2)
        self.assertEqual(self.cli.list_account_aliases(), [])

        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.cmd_import(SimpleNamespace(file=bundle_path, alias=None, overwrite=False))

        self.assertEqual(self.cli.list_account_aliases(), ["agy01", "agy02"])
        cfg = self.cli.load_config()
        self.assertEqual(cfg.get("active_account"), "agy01")
        self.assertEqual(cfg.get("default_account"), "agy01")
        self.assertTrue(os.path.isfile(self.cli.get_active_token_path()))

        iso_tok = os.path.join(
            self.home2, ".agyc_homes", "agy02", ".gemini", "antigravity-cli", "antigravity-oauth-token"
        )
        self.assertTrue(os.path.isfile(iso_tok))
        with open(iso_tok, "r", encoding="utf-8") as f:
            tok_payload = json.load(f)
        self.assertEqual(tok_payload["token"]["access_token"], "tok2")

    def test_35_import_with_alias_override_and_rejects_multi(self) -> None:
        import contextlib
        import io
        from types import SimpleNamespace

        self._seed_account("agy01", "dev1@gmail.com", "tok1")
        single_bundle = os.path.join(self.root_dir, "single.json")
        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.cmd_export(SimpleNamespace(alias="agy01", output=single_bundle))

        self._seed_account("agy02", "dev2@gmail.com", "tok2")
        multi_bundle = os.path.join(self.root_dir, "multi.json")
        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.cmd_export(SimpleNamespace(alias=None, output=multi_bundle))

        self._switch_home(self.home2)
        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.cmd_import(SimpleNamespace(file=single_bundle, alias="work01", overwrite=False))
        acc = self.cli.load_account("work01")
        self.assertIsNotNone(acc)
        self.assertEqual(acc["alias"], "work01")
        self.assertEqual(acc["email"], "dev1@gmail.com")

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                self.cli.cmd_import(SimpleNamespace(file=multi_bundle, alias="work02", overwrite=False))
        self.assertEqual(ctx.exception.code, 1)

    def test_36_import_rejects_duplicate_without_overwrite_and_replaces_with_overwrite(self) -> None:
        import contextlib
        import io
        from types import SimpleNamespace

        self._seed_account("agy01", "dev1@gmail.com", "new_tok")
        bundle_path = os.path.join(self.root_dir, "single_new.json")
        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.cmd_export(SimpleNamespace(alias="agy01", output=bundle_path))

        # En home2 ya existe agy01 con old_tok
        self._switch_home(self.home2)
        self._seed_account("agy01", "dev1@gmail.com", "old_tok")

        # Sin --overwrite debe rechazar el duplicado sin sobrescribir
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                self.cli.cmd_import(SimpleNamespace(file=bundle_path, alias=None, overwrite=False))
        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(
            self.cli.load_account("agy01")["token_data"]["token"]["access_token"],
            "old_tok",
        )

        # Duplicado por email bajo otro alias sin --overwrite también debe rechazarse
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx2:
                self.cli.cmd_import(SimpleNamespace(file=bundle_path, alias="agy99", overwrite=False))
        self.assertEqual(ctx2.exception.code, 1)
        self.assertIsNone(self.cli.load_account("agy99"))

        # Con --overwrite debe reemplazar el token y sincronizar el HOME aislado
        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.cmd_import(SimpleNamespace(file=bundle_path, alias=None, overwrite=True))
        self.assertEqual(
            self.cli.load_account("agy01")["token_data"]["token"]["access_token"],
            "new_tok",
        )
        iso_tok = os.path.join(
            self.home2, ".agyc_homes", "agy01", ".gemini", "antigravity-cli", "antigravity-oauth-token"
        )
        with open(iso_tok, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f)["token"]["access_token"], "new_tok")

    def test_37_windows_launch_and_wrapper_set_ssh_tty_keyring_bypass(self) -> None:
        agy_cmd_path = os.path.join(REPO_ROOT, "bin", "agy.cmd")
        with open(agy_cmd_path, "r", encoding="utf-8") as f:
            agy_cmd_text = f.read()
        self.assertIn("SSH_TTY=/dev/pts/0", agy_cmd_text)
        self.assertIn("SSH_TTY=/dev/pts/0", self.cli._default_agy_cmd_content())

        self._seed_account("agy01", "dev1@gmail.com", "tok_win_bypass")
        fake_real = os.path.join(self.home1, "AppData", "Local", "agy", "bin", "agy.exe")
        os.makedirs(os.path.dirname(fake_real), exist_ok=True)
        with open(fake_real, "wb") as f:
            f.write(b"MZ")

        captured: dict[str, object] = {}

        class _FakeProc:
            pid = 42424
            returncode = 0

            def wait(self) -> int:
                return 0

            def poll(self) -> int:
                return 0

        orig_popen = self.cli.subprocess.Popen

        def _fake_popen(cmd_args, env=None, **kwargs):
            if cmd_args and cmd_args[0] == fake_real:
                captured["cmd_args"] = list(cmd_args)
                captured["env"] = dict(env or {})
                return _FakeProc()
            return orig_popen(cmd_args, env=env, **kwargs)

        clean_env = {k: v for k, v in os.environ.items() if k not in ("SSH_TTY", "SSH_CLIENT")}
        with mock.patch.dict(os.environ, clean_env, clear=True), mock.patch.object(
            self.cli.platform, "IS_WINDOWS", True
        ), mock.patch.object(
            self.cli, "_find_real_agy_binary", return_value=fake_real
        ), mock.patch.object(
            self.cli.subprocess, "Popen", side_effect=_fake_popen
        ):
            with self.assertRaises(SystemExit) as ctx:
                self.cli.launch_real_agy(["--version"], alias="agy01")

        self.assertEqual(ctx.exception.code, 0)
        child_env = captured["env"]
        expected_iso = os.path.join(self.home1, ".agyc_homes", "agy01")
        self.assertEqual(child_env.get("SSH_TTY"), "/dev/pts/0")
        self.assertEqual(child_env.get("USERPROFILE"), expected_iso)
        self.assertEqual(child_env.get("HOME"), expected_iso)
        self.assertEqual(child_env.get("AGYC_ACCOUNT"), "agy01")

    def test_38_win32_herdr_named_pipe_and_ancestor_pid(self) -> None:
        from lib.platform import linux as lin, win32 as w32

        self.assertTrue(hasattr(agyc_platform, "find_ancestor_agy_pid"))
        self.assertTrue(hasattr(lin, "find_ancestor_agy_pid"))
        self.assertTrue(hasattr(w32, "find_ancestor_agy_pid"))

        fake_tree = {
            300: ("python.exe", 200),
            200: ("cmd.exe", 100),
            100: ("agy.exe", 50),
            50: ("powershell.exe", 10),
        }
        with mock.patch.object(w32, "_list_win32_processes_with_ppid", return_value=fake_tree):
            self.assertEqual(w32.find_ancestor_agy_pid(start_pid=300), 100)
            self.assertIsNone(w32.find_ancestor_agy_pid(start_pid=50))

        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            pipe_name = f"\\\\.\\pipe\\agyc_test_{os.getpid()}_{id(self)}"
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.CreateNamedPipeW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.c_void_p,
            ]
            k32.CreateNamedPipeW.restype = wintypes.HANDLE
            k32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
            k32.ConnectNamedPipe.restype = wintypes.BOOL
            k32.ReadFile.argtypes = [
                wintypes.HANDLE,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.c_void_p,
            ]
            k32.ReadFile.restype = wintypes.BOOL
            k32.WriteFile.argtypes = [
                wintypes.HANDLE,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.c_void_p,
            ]
            k32.WriteFile.restype = wintypes.BOOL
            k32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
            k32.FlushFileBuffers.restype = wintypes.BOOL
            k32.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
            k32.DisconnectNamedPipe.restype = wintypes.BOOL
            k32.CloseHandle.argtypes = [wintypes.HANDLE]
            k32.CloseHandle.restype = wintypes.BOOL

            h_pipe = k32.CreateNamedPipeW(
                pipe_name,
                0x00000003,  # PIPE_ACCESS_DUPLEX
                0x00000000,  # PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT
                1,
                4096,
                4096,
                500,
                None,
            )
            invalid_handle = wintypes.HANDLE(-1).value
            self.assertNotEqual(h_pipe, invalid_handle)

            seen_req: list[dict] = []

            def _serve_pipe() -> None:
                try:
                    ok = k32.ConnectNamedPipe(h_pipe, None)
                    if not ok and ctypes.get_last_error() != 535:  # ERROR_PIPE_CONNECTED
                        return
                    buf = ctypes.create_string_buffer(4096)
                    read_n = wintypes.DWORD(0)
                    if k32.ReadFile(h_pipe, buf, 4096, ctypes.byref(read_n), None) and read_n.value > 0:
                        raw = buf.raw[: int(read_n.value)].decode("utf-8", errors="replace").strip()
                        seen_req.append(json.loads(raw))
                        reply = (
                            json.dumps({"id": "1", "result": {"type": "pane_list", "panes": [{"pane_id": "w9:p1"}]}})
                            + "\n"
                        ).encode("utf-8")
                        wr_n = wintypes.DWORD(0)
                        out_buf = ctypes.create_string_buffer(reply, len(reply))
                        k32.WriteFile(h_pipe, out_buf, len(reply), ctypes.byref(wr_n), None)
                        k32.FlushFileBuffers(h_pipe)
                    k32.DisconnectNamedPipe(h_pipe)
                finally:
                    k32.CloseHandle(h_pipe)

            srv_t = threading.Thread(target=_serve_pipe, daemon=True)
            srv_t.start()
            resp = w32.query_herdr_ipc(pipe_name, {"id": "1", "method": "pane.list", "params": {}}, timeout=0.5)
            srv_t.join(timeout=2)

            self.assertIsNotNone(resp)
            self.assertEqual(resp["result"]["panes"][0]["pane_id"], "w9:p1")
            self.assertEqual(seen_req[0]["method"], "pane.list")


if __name__ == "__main__":
    unittest.main()
