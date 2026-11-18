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
        for k in ("ANTIGRAVITY_HOME", "AGY_CONFIG_DIR", "HERDR_SOCKET_PATH", "HERDR_PANE_ID"):
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

        for d in (acc_dir, cache_dir, locks_dir):
            mode = stat.S_IMODE(os.stat(d).st_mode)
            self.assertEqual(mode, 0o700, f"Expected 0700 on {d}, got {oct(mode)}")

    def test_05_atomic_write_json_enforces_0600_and_valid_payload(self) -> None:
        target = os.path.join(self.tmp_dir, "nested", "secret_account.json")
        payload = {"alias": "agy02", "email": "dev@example.com", "locked": False}
        agyc_core.atomic_write_json(target, payload, mode=0o600, indent=2)

        self.assertTrue(os.path.isfile(target))
        file_mode = stat.S_IMODE(os.stat(target).st_mode)
        self.assertEqual(file_mode, 0o600)
        with open(target, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded, payload)

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

        sock_path = os.path.join(self.tmp_dir, "herdr.sock")
        herdr_response = {
            "id": "1",
            "result": {
                "panes": [
                    {"pane_id": "w3:p2", "label": "Principal", "tab_id": "w3:t1", "focused": True},
                    {"pane_id": "w3:p5", "label": "Soporte", "tab_id": "w3:t1", "focused": False},
                    # Dead pane in Herdr where agy-real is no longer running in /proc -> discarded
                    {"pane_id": "w3:pDead", "label": "Viejo", "tab_id": "w3:t2", "focused": False, "agent": "agy"},
                ]
            },
        }

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


if __name__ == "__main__":
    unittest.main()
