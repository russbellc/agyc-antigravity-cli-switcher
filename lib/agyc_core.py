"""
agyc_core: Shared pure-stdlib core for agyc, agyc-statusline, and agyc-topbar.

Designed for <2ms import latency under `python3 -S` (heavy modules such as
`json`, `pwd`, and `_socket` are imported lazily inside functions).
"""

from __future__ import annotations

import math
import os
import time
from datetime import datetime, timezone

ANTIGRAVITY_UA = "antigravity/1.5.10 (aidev_client; os_type=linux; arch=amd64; cl=999999999)"

RESERVED_ALIASES: frozenset[str] = frozenset({
    "config",
    "agy",
    "agi",
    "agyc",
    "agy-real",
    "agyc-statusline",
    "agyc-titleline",
    "agyc-topbar",
    "list",
    "switch",
    "use",
    "default",
    "set-default",
    "add",
    "renew",
    "reauth",
    "login",
    "capture",
    "import-current",
    "remove",
    "rm",
    "quota",
    "auto",
    "lock",
    "unlock",
    "note",
    "tag",
    "label",
    "doctor",
    "wipe",
    "clean",
    "purge",
    "update",
    "upgrade",
    "help",
    "status",
    "version",
    "json",
    "true",
    "false",
    "null",
    "none",
})

SAFE_QUOTA_KEYS: tuple[str, ...] = (
    "gemini_5h_fraction",
    "gemini_5h_reset",
    "gemini_weekly_fraction",
    "gemini_weekly_reset",
    "gemini_disabled",
    "claude_5h_fraction",
    "claude_5h_reset",
    "claude_weekly_fraction",
    "claude_weekly_reset",
    "claude_disabled",
    "plan_type",
    "tier_id",
    "tier_name",
    "supports_carbon",
    "fetched_at",
    "cached_at",
)

_SECRET_SUBSTRINGS: tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "credential",
    "auth_code",
    "private_key",
    "cookie",
    "authorization",
)


# ---------------------------------------------------------------------------
# 1. Paths, Alias Validation & Atomic / Sanitized Persistence (0700 / 0600)
# ---------------------------------------------------------------------------


def _has_agyc_homes_segment(path: str) -> bool:
    s = (path or "").strip()
    return "/.agyc_homes/" in s or s.rstrip("/").endswith("/.agyc_homes")


def _strip_agyc_homes(path: str) -> str:
    s = (path or "").strip()
    if "/.agyc_homes/" in s:
        s = s.split("/.agyc_homes/", 1)[0]
    elif s.endswith("/.agyc_homes"):
        s = s[: -len("/.agyc_homes")]
    elif s.rstrip("/").endswith("/.agyc_homes"):
        s = s.rstrip("/")[: -len("/.agyc_homes")]
    return s.rstrip("/") or "/"


def resolve_real_home() -> str:
    """Resolves real user HOME ignoring isolated `/.agyc_homes/` values."""
    for env_key in ("AGYC_REAL_HOME", "REAL_HOME"):
        val = os.environ.get(env_key, "").strip()
        if val and val != "~" and not _has_agyc_homes_segment(val):
            cleaned = val.rstrip("/") or "/"
            if os.path.isdir(cleaned):
                return cleaned

    try:
        import pwd

        pw_dir = pwd.getpwuid(os.getuid()).pw_dir
        if pw_dir:
            cleaned_pw = _strip_agyc_homes(pw_dir)
            if cleaned_pw and os.path.isdir(cleaned_pw):
                return cleaned_pw
    except Exception:
        pass

    home_env = os.environ.get("HOME", "").strip()
    if home_env and home_env != "~" and not _has_agyc_homes_segment(home_env):
        cleaned_home = home_env.rstrip("/") or "/"
        if os.path.isdir(cleaned_home):
            return cleaned_home

    return "/home/aidev"


def _ensure_private_dir(path: str, mode: int = 0o700) -> str:
    os.makedirs(path, mode=mode, exist_ok=True)
    try:
        os.chmod(path, mode)
    except OSError:
        pass
    return path


def get_base_dir(real_home: str | None = None) -> str:
    """Returns Antigravity CLI base directory (`~/.gemini/antigravity-cli`), immune to `.agyc_homes`."""
    rh = _strip_agyc_homes(real_home) if real_home else resolve_real_home()
    candidates: list[str | None] = []
    if real_home is None:
        candidates.append(os.environ.get("ANTIGRAVITY_HOME"))
        candidates.append(os.environ.get("AGY_CONFIG_DIR"))
    candidates.append(os.path.join(rh, ".gemini", "antigravity-cli"))
    candidates.append(os.path.join(rh, "snap", "antigravity-cli", "common", ".gemini", "antigravity-cli"))

    for cand in candidates:
        if cand and not _has_agyc_homes_segment(cand) and os.path.exists(cand):
            return cand.rstrip("/") or "/"

    default_path = os.path.join(rh, ".gemini", "antigravity-cli")
    return _ensure_private_dir(default_path, 0o700)


def get_accounts_dir(real_home: str | None = None) -> str:
    """Returns `~/.gemini/antigravity-cli/accounts` with strict `0700` permissions."""
    return _ensure_private_dir(os.path.join(get_base_dir(real_home), "accounts"), 0o700)


def get_cache_dir(real_home: str | None = None) -> str:
    """Returns `~/.cache/agyc` with strict `0700` permissions."""
    rh = _strip_agyc_homes(real_home) if real_home else resolve_real_home()
    return _ensure_private_dir(os.path.join(rh, ".cache", "agyc"), 0o700)


def get_locks_dir(real_home: str | None = None) -> str:
    """Returns `~/.cache/agyc/locks` with strict `0700` permissions."""
    return _ensure_private_dir(os.path.join(get_cache_dir(real_home), "locks"), 0o700)


def normalize_alias(alias: str) -> str:
    """Normalizes correlative aliases (`agy1` -> `agy01`, `agi2` -> `agy02`)."""
    if not isinstance(alias, str):
        return ""
    s = alias.strip()
    if not s:
        return ""
    low = s.lower()
    if len(low) >= 4 and (low.startswith("agy") or low.startswith("agi")):
        tail = low[3:]
        if tail.isdigit():
            return f"agy{int(tail):02d}"
    return s


def _is_valid_alias_chars(s: str) -> bool:
    if not s or len(s) > 32:
        return False
    first = s[0]
    if not (first.isascii() and first.isalnum()):
        return False
    for ch in s:
        if not ((ch.isascii() and ch.isalnum()) or ch in ("_", "-")):
            return False
    return True


def validate_alias(alias: str) -> str:
    """Strictly validates alias against path traversal, invalid characters, and reserved names."""
    if not isinstance(alias, str):
        raise ValueError("Alias inválido: debe ser texto no vacío.")
    raw = alias.strip()
    if not raw or ".." in raw or "/" in raw or "\\" in raw or "\x00" in raw:
        raise ValueError(
            f"Alias inválido '{alias}': debe cumplir ^[a-zA-Z0-9][a-zA-Z0-9_-]{{0,31}}$ (sin '..' ni '/')."
        )
    norm = normalize_alias(raw)
    if not _is_valid_alias_chars(norm):
        raise ValueError(
            f"Alias inválido '{alias}': debe cumplir ^[a-zA-Z0-9][a-zA-Z0-9_-]{{0,31}}$."
        )
    if norm.lower() in RESERVED_ALIASES:
        raise ValueError(
            f"El alias '{norm}' está reservado por el sistema. Usa otro nombre (ej. agy01, work)."
        )
    return norm


def extract_agy_alias(text: str) -> str | None:
    """Extracts word-bounded `agy01`..`agy99` (normalized) from arbitrary text without regex."""
    if not text or not isinstance(text, str):
        return None
    low = text.lower()
    idx = 0
    n = len(low)
    while True:
        pos = low.find("agy", idx)
        if pos == -1:
            return None
        if pos > 0 and (low[pos - 1].isalnum() or low[pos - 1] == "_"):
            idx = pos + 3
            continue
        end = pos + 3
        while end < n and low[end].isdigit():
            end += 1
        digits_len = end - (pos + 3)
        if 1 <= digits_len <= 3 and (end == n or not (low[end].isalnum() or low[end] == "_")):
            return f"agy{int(low[pos + 3 : end]):02d}"
        idx = pos + 3


def atomic_write_json(
    path: str,
    payload: dict,
    mode: int = 0o600,
    indent: int | None = None,
) -> None:
    """Atomically writes JSON to `path` via temp file + `os.replace` with strict `mode` (default `0600`)."""
    import json

    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        _ensure_private_dir(parent, 0o700)

    tmp_path = f"{path}.tmp.{os.getpid()}.{time.time_ns()}"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=indent, ensure_ascii=False)
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _scrub_secrets(value: object) -> object:
    """Recursively strips any dictionary keys resembling OAuth tokens or secrets."""
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for k, v in value.items():
            k_str = str(k)
            k_low = k_str.lower()
            if any(sec in k_low for sec in _SECRET_SUBSTRINGS):
                continue
            cleaned[k_str] = _scrub_secrets(v)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_scrub_secrets(item) for item in value]
    return value


def sanitize_account_for_json(
    alias: str,
    data: dict | None = None,
    active_account: str | None = None,
    default_account: str | None = None,
    active_panes: list[str] | None = None,
) -> dict:
    """Builds a strictly sanitized account representation free of tokens/secrets, including `active_panes`."""
    if isinstance(alias, dict) and data is None:
        acc = alias
        alias_str = str(acc.get("alias") or "")
    else:
        acc = data if isinstance(data, dict) else {}
        alias_str = str(alias or "")
    norm_al = normalize_alias(alias_str) or normalize_alias(str(acc.get("alias") or "")) or alias_str
    act_norm = normalize_alias(active_account) if active_account else None
    def_norm = normalize_alias(default_account) if default_account else None

    raw_q = acc.get("quota") if isinstance(acc.get("quota"), dict) else {}
    now_dt = datetime.now(timezone.utc)

    clean_quota: dict[str, object] = {}
    for k in SAFE_QUOTA_KEYS:
        if k in raw_q and not any(sec in k.lower() for sec in _SECRET_SUBSTRINGS):
            clean_quota[k] = _scrub_secrets(raw_q[k])

    for fam in ("gemini", "claude"):
        f5_key, r5_key = f"{fam}_5h_fraction", f"{fam}_5h_reset"
        fw_key, rw_key = f"{fam}_weekly_fraction", f"{fam}_weekly_reset"
        if f5_key in clean_quota or r5_key in clean_quota:
            f5, r5 = normalize_window(
                clean_quota.get(f5_key),  # type: ignore[arg-type]
                clean_quota.get(r5_key),  # type: ignore[arg-type]
                now_dt=now_dt,
            )
            clean_quota[f5_key] = f5
            clean_quota[r5_key] = r5
        if fw_key in clean_quota or rw_key in clean_quota:
            fw, rw = normalize_window(
                clean_quota.get(fw_key),  # type: ignore[arg-type]
                clean_quota.get(rw_key),  # type: ignore[arg-type]
                now_dt=now_dt,
            )
            clean_quota[fw_key] = fw
            clean_quota[rw_key] = rw

    raw_supports_carbon = clean_quota.get("supports_carbon")
    if raw_supports_carbon is None:
        raw_supports_carbon = acc.get("supports_carbon")

    raw_plan = clean_quota.get("plan_type") or acc.get("plan_type")
    if raw_plan:
        plan_type = str(raw_plan).upper()
    elif raw_supports_carbon:
        plan_type = "ULTRA"
    else:
        plan_type = "FREE"

    supports_carbon = bool(raw_supports_carbon or plan_type == "ULTRA")
    tier_id = str(
        clean_quota.get("tier_id")
        or acc.get("tier_id")
        or ("g1-ultra-tier" if plan_type == "ULTRA" else ("g1-pro-tier" if plan_type == "PRO" else "free-tier"))
    )
    tier_name = str(clean_quota.get("tier_name") or acc.get("tier_name") or "Antigravity")

    clean_quota["plan_type"] = plan_type
    clean_quota["tier_id"] = tier_id
    clean_quota["tier_name"] = tier_name
    clean_quota["supports_carbon"] = supports_carbon

    safe_panes = _scrub_secrets(list(active_panes or []))

    return {
        "alias": norm_al,
        "email": str(acc.get("email") or ""),
        "name": str(acc.get("name") or ""),
        "plan_type": plan_type,
        "tier_id": tier_id,
        "tier_name": tier_name,
        "supports_carbon": supports_carbon,
        "is_active": bool(act_norm and norm_al == act_norm),
        "is_default": bool(def_norm and norm_al == def_norm),
        "is_revoked": bool(acc.get("is_revoked", False)),
        "locked": bool(acc.get("locked", False)),
        "lock_reason": str(acc.get("lock_reason") or ""),
        "note": str(acc.get("note") or ""),
        "active_panes": safe_panes if isinstance(safe_panes, list) else [],
        "quota": clean_quota,
        "updated_at": acc.get("updated_at"),
    }


# ---------------------------------------------------------------------------
# 2. Quota Window Normalization & Post-Compaction O(1) Context Estimation
# ---------------------------------------------------------------------------


def parse_iso_datetime(iso_str: str | None) -> datetime | None:
    """Parses an ISO-8601 timestamp into a UTC-aware `datetime` (or `None` if invalid)."""
    if not iso_str or not isinstance(iso_str, str):
        return None
    s = iso_str.strip()
    if not s:
        return None
    try:
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        if "." in s:
            head, rest = s.split(".", 1)
            tz_sep_pos = -1
            tz_sign = ""
            for sign in ("+", "-"):
                idx = rest.find(sign)
                if idx != -1:
                    tz_sep_pos = idx
                    tz_sign = sign
                    break
            if tz_sep_pos != -1:
                frac_digits = rest[:tz_sep_pos]
                tz_tail = rest[tz_sep_pos + 1 :]
                if frac_digits.isdigit():
                    micros = frac_digits[:6].ljust(6, "0")
                    s = f"{head}.{micros}{tz_sign}{tz_tail}"
            elif rest.isdigit():
                micros = rest[:6].ljust(6, "0")
                s = f"{head}.{micros}"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def normalize_window(
    frac: float | None,
    reset_str: str | None,
    now_dt: datetime | None = None,
) -> tuple[float | None, str | None]:
    """
    Normalizes a quota window `(fraction, resetTime)`:
      - Expired `reset_str` (`<= now_dt`) -> `(1.0, None)`
      - `frac >= 0.9995` -> `(1.0, None)`
      - Otherwise `(clamp(frac, 0.0, 1.0), valid_reset_str)`
    """
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)

    clean_reset: str | None = None
    if reset_str and isinstance(reset_str, str):
        rst_dt = parse_iso_datetime(reset_str)
        if rst_dt is not None:
            if rst_dt <= now_dt:
                return (1.0, None)
            clean_reset = reset_str.strip()

    if frac is None or isinstance(frac, bool):
        return (None, clean_reset)

    try:
        f = max(0.0, min(1.0, float(frac)))
    except (TypeError, ValueError):
        return (None, clean_reset)

    if f >= 0.9995:
        return (1.0, None)
    return (f, clean_reset)


def pct_display(frac: float | None) -> int:
    """Integer percentage display: `100` if `None` or `>=0.9995`, `0` if `<=0.0005`, else `floor(frac*100)`."""
    if frac is None or isinstance(frac, bool):
        return 100
    try:
        f = max(0.0, min(1.0, float(frac)))
    except (TypeError, ValueError):
        return 100
    if f >= 0.9995:
        return 100
    if f <= 0.0005:
        return 0
    return min(99, int(math.floor(f * 100.0 + 1e-9)))


def default_max_tokens_for_model(model_name: str) -> int:
    """Returns context window size for the given model display name or slug."""
    m = (model_name or "").lower()
    if "flash-image" in m or "pro-image" in m or "image" in m:
        return 65_536
    if any(k in m for k in ("gpt-oss", "120b", "gpt")):
        return 131_072
    if any(k in m for k in ("claude", "sonnet", "opus", "haiku")):
        if "haiku" in m:
            return 200_000
        if any(v in m for v in ("4-6", "4.6", "5-5", "5.5")):
            return 250_000
        return 200_000
    return 1_048_576


def _safe_nonneg_int(val: object) -> int:
    if val is None or isinstance(val, bool):
        return 0
    try:
        return max(0, int(val))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _first_present(sources: tuple[dict, ...], keys: tuple[str, ...]) -> object:
    for src in sources:
        for k in keys:
            val = src.get(k)
            if val is not None and not isinstance(val, bool):
                return val
    return None


def _scan_transcript_window(
    raw_bytes: bytes,
    drop_first_partial: bool,
    max_tokens: int,
) -> tuple[tuple[float, int, int] | None, int]:
    import json

    lines = raw_bytes.splitlines()
    if drop_first_partial and lines:
        lines = lines[1:]
    trailing_chars = 0

    for raw_line in reversed(lines):
        line_str = raw_line.decode("utf-8", errors="ignore").strip()
        if not line_str:
            continue
        try:
            entry = json.loads(line_str)
        except Exception:
            trailing_chars += len(line_str)
            continue
        if not isinstance(entry, dict):
            continue

        etype = str(entry.get("type") or "").upper()
        raw_content = entry.get("content")
        if isinstance(raw_content, str):
            content_str = raw_content
        elif raw_content is not None:
            content_str = json.dumps(raw_content, ensure_ascii=False)
        else:
            content_str = ""

        raw_summary = entry.get("summary")
        summary_str = raw_summary if isinstance(raw_summary, str) else ""

        # 1. Stop immediately at any compaction boundary (never count pre-compaction history)
        if (
            etype in ("CHECKPOINT", "CONTEXT_SUMMARY", "COMPACTION")
            or "# Resuming from a compaction" in content_str
            or "<CONTEXT_SUMMARY>" in content_str
            or bool(entry.get("is_compaction") or entry.get("compacted"))
        ):
            explicit_cp = _first_present((entry,), ("token_count", "summary_tokens", "input_tokens"))
            if explicit_cp is not None and _safe_nonneg_int(explicit_cp) > 0:
                base_tokens = _safe_nonneg_int(explicit_cp)
            else:
                base_tokens = 16_000 + int((len(content_str) + len(summary_str)) / 4.0)
            est = base_tokens + int(trailing_chars / 4.0)
            frac = min(1.0, max(0.0, est / float(max_tokens)))
            return (frac, est, max_tokens), trailing_chars

        # 2. Latest PLANNER_RESPONSE carrying real LLM token usage counters
        usage_dict = entry.get("usage") if isinstance(entry.get("usage"), dict) else {}
        tok_usage = entry.get("token_usage") if isinstance(entry.get("token_usage"), dict) else {}
        sources = (entry, usage_dict, tok_usage)

        in_tok = _first_present(sources, ("input_tokens", "prompt_tokens"))
        cr_tok = _first_present(
            sources,
            ("cache_read_tokens", "cache_read_input_tokens", "cached_content_token_count"),
        )
        cc_tok = _first_present(sources, ("cache_creation_input_tokens", "cache_creation_tokens"))
        out_tok = _first_present(sources, ("output_tokens", "completion_tokens", "candidates_token_count"))

        if etype == "PLANNER_RESPONSE" and (in_tok is not None or cr_tok is not None):
            est = (
                _safe_nonneg_int(in_tok)
                + _safe_nonneg_int(cr_tok)
                + _safe_nonneg_int(cc_tok)
                + _safe_nonneg_int(out_tok)
                + int(trailing_chars / 4.0)
            )
            frac = min(1.0, max(0.0, est / float(max_tokens)))
            return (frac, est, max_tokens), trailing_chars

        step_chars = len(content_str) + len(summary_str)
        thinking = entry.get("thinking")
        if isinstance(thinking, str):
            step_chars += len(thinking)
        if entry.get("tool_calls"):
            try:
                step_chars += len(json.dumps(entry["tool_calls"], ensure_ascii=False))
            except Exception:
                pass
        trailing_chars += step_chars

    return None, trailing_chars


def estimate_context_from_transcript(transcript_path: str, max_tokens: int) -> tuple[float, int, int]:
    """
    O(1) reverse tail context estimator (`128 KB` -> `512 KB` from EOF).
    Honors compaction boundaries (`CHECKPOINT`, `CONTEXT_SUMMARY`, `# Resuming from a compaction`)
    and exact `PLANNER_RESPONSE` token counters without reading pre-compaction megabytes.
    """
    if max_tokens <= 0:
        max_tokens = 1_048_576
    if not transcript_path or not os.path.isfile(transcript_path):
        return (0.0, 0, max_tokens)

    try:
        file_size = os.path.getsize(transcript_path)
    except OSError:
        return (0.0, 0, max_tokens)

    if file_size <= 0:
        return (0.0, 0, max_tokens)

    last_trailing = 0
    try:
        with open(transcript_path, "rb") as f:
            for win_bytes in (131_072, 524_288):
                offset = max(0, file_size - win_bytes)
                f.seek(offset)
                buf = f.read(file_size - offset)
                res, last_trailing = _scan_transcript_window(
                    buf,
                    drop_first_partial=(offset > 0),
                    max_tokens=max_tokens,
                )
                if res is not None:
                    return res
                if offset == 0:
                    break
    except Exception:
        return (0.0, 0, max_tokens)

    est = int(last_trailing / 4.0) if last_trailing > 0 else int(min(file_size, 524_288) / 4.0)
    frac = min(1.0, max(0.0, est / float(max_tokens)))
    return (frac, est, max_tokens)


# ---------------------------------------------------------------------------
# 3. Live Detection of Active Herdr Panes (`scan_active_herdr_panes`)
# ---------------------------------------------------------------------------


def _extract_alias_from_home_path(path_val: str) -> str | None:
    if not path_val:
        return None
    marker = "/.agyc_homes/"
    idx = path_val.find(marker)
    if idx != -1:
        rest = path_val[idx + len(marker) :]
        seg = rest.split("/", 1)[0].strip()
        if seg:
            try:
                return validate_alias(seg)
            except ValueError:
                pass
    return extract_agy_alias(path_val)


def _is_elf_agy_binary(proc_dir: str, comm: bytes) -> bool:
    if comm == b"agy-real":
        return True
    if comm not in (b"agy", b"antigravity"):
        return False
    exe_link = os.path.join(proc_dir, "exe")
    try:
        target = os.readlink(exe_link)
        base = os.path.basename(target).lower()
        if base.startswith(("python", "bash", "sh", "dash", "zsh", "node", "perl")):
            return False
    except OSError:
        pass
    try:
        with open(exe_link, "rb") as ef:
            return ef.read(4) == b"\x7fELF"
    except OSError:
        return False


def _read_proc_state_only(proc_dir: str) -> bytes:
    """Reads 1-byte task state (`R`, `S`, `D`, `T`, `Z`, ...) only for matched `agy` processes."""
    try:
        with open(os.path.join(proc_dir, "stat"), "rb") as sf:
            data = sf.read(128)
        rparen = data.rfind(b")")
        if rparen != -1 and rparen + 3 <= len(data):
            return data[rparen + 2 : rparen + 3] or b"S"
    except OSError:
        pass
    return b"S"


def _read_default_active_account(rh: str) -> str | None:
    import json

    for cand in (
        os.path.join(rh, ".gemini", "antigravity-cli", "accounts", "config.json"),
        os.path.join(rh, "snap", "antigravity-cli", "common", ".gemini", "antigravity-cli", "accounts", "config.json"),
    ):
        if os.path.isfile(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                raw = cfg.get("active_account") or cfg.get("default_account")
                if isinstance(raw, str) and raw.strip():
                    return normalize_alias(raw)
            except Exception:
                pass
    return None


def _query_herdr_pane_list(sock_path: str, timeout: float = 0.06) -> tuple[bool, dict[str, dict]]:
    import _socket
    import json

    if not sock_path or not os.path.exists(sock_path):
        return False, {}

    s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(sock_path)
        s.sendall(b'{"id":"1","method":"pane.list","params":{}}\n')
        chunks: list[bytes] = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        raw_line = b"".join(chunks).split(b"\n", 1)[0]
        if not raw_line:
            return False, {}
        resp = json.loads(raw_line.decode("utf-8", errors="replace"))
        panes = (resp.get("result") or {}).get("panes")
        if not isinstance(panes, list):
            return False, {}
        by_id: dict[str, dict] = {}
        for p in panes:
            if isinstance(p, dict) and isinstance(p.get("pane_id"), str) and p["pane_id"]:
                by_id[p["pane_id"]] = p
        return True, by_id
    except Exception:
        return False, {}
    finally:
        try:
            s.close()
        except Exception:
            pass


def scan_active_herdr_panes(
    real_home: str | None = None,
    *,
    proc_root: str = "/proc",
    herdr_socket_path: str | None = None,
) -> dict[str, list[dict]]:
    """
    Scans `/proc/[0-9]*` for live `agy-real` (or ELF `agy`) processes owned by current UID,
    cross-references with Herdr UNIX socket (`pane.list`, timeout `0.06s`), discards dead panes,
    deduplicates subprocesses per `pane_id`, and returns `dict[alias, list[dict]]` in `<8ms`.
    """
    rh = _strip_agyc_homes(real_home) if real_home else resolve_real_home()
    uid = os.getuid()

    # Map pane_id -> (priority_tuple, pid, env_alias_or_none)
    live_by_pane: dict[str, tuple[tuple[int, int, int], int, str | None]] = {}

    try:
        with os.scandir(proc_root) as it:
            for entry in it:
                name = entry.name
                if not name.isdigit():
                    continue
                try:
                    if entry.stat(follow_symlinks=False).st_uid != uid:
                        continue
                    pdir = entry.path
                    fd_c = os.open(f"{pdir}/comm", os.O_RDONLY)
                    try:
                        comm = os.read(fd_c, 32).strip()
                    finally:
                        os.close(fd_c)
                    if not _is_elf_agy_binary(pdir, comm):
                        continue
                    state = _read_proc_state_only(pdir)
                    if state in (b"Z", b"X"):
                        continue

                    fd_e = os.open(f"{pdir}/environ", os.O_RDONLY)
                    try:
                        env_raw = os.read(fd_e, 65536)
                    finally:
                        os.close(fd_e)
                except OSError:
                    continue

                pane_id: str | None = None
                env_alias: str | None = None
                for item in env_raw.split(b"\x00"):
                    if item.startswith(b"HERDR_PANE_ID="):
                        pane_id = item[14:].decode("utf-8", errors="ignore").strip()
                    elif item.startswith((b"HOME=", b"ANTIGRAVITY_APP_DATA_DIR=")):
                        val = item.split(b"=", 1)[1].decode("utf-8", errors="ignore")
                        cand = _extract_alias_from_home_path(val)
                        if cand:
                            env_alias = cand
                    elif item.startswith((b"AGYC_ACCOUNT=", b"AGYC_ALIAS=")) and not env_alias:
                        val = item.split(b"=", 1)[1].decode("utf-8", errors="ignore").strip()
                        if val:
                            try:
                                env_alias = validate_alias(val)
                            except ValueError:
                                pass

                if not pane_id:
                    continue

                pid = int(name)
                is_running = 1 if state not in (b"T", b"t") else 0
                has_explicit_alias = 1 if env_alias else 0
                prio = (is_running, has_explicit_alias, pid)

                prev = live_by_pane.get(pane_id)
                if prev is None or prio > prev[0]:
                    live_by_pane[pane_id] = (prio, pid, env_alias)
    except OSError:
        return {}

    if not live_by_pane:
        return {}

    sock_path = (
        herdr_socket_path
        if herdr_socket_path is not None
        else (os.environ.get("HERDR_SOCKET_PATH") or os.path.join(rh, ".config", "herdr", "herdr.sock"))
    )
    herdr_online, herdr_panes = _query_herdr_pane_list(sock_path, timeout=0.06)
    fallback_alias: str | None = None
    fallback_loaded = False

    result: dict[str, list[dict]] = {}
    for pane_id, (_prio, pid, env_alias) in live_by_pane.items():
        if herdr_online and pane_id not in herdr_panes:
            # Pane was closed in Herdr; ignore stale detached child process
            continue

        hp = herdr_panes.get(pane_id, {})
        alias = env_alias
        if not alias and hp:
            for meta_key in ("display_agent", "terminal_title_stripped", "terminal_title", "label"):
                meta_val = hp.get(meta_key)
                if isinstance(meta_val, str) and meta_val:
                    found = extract_agy_alias(meta_val)
                    if found:
                        alias = found
                        break

        if not alias:
            if not fallback_loaded:
                fallback_alias = _read_default_active_account(rh)
                fallback_loaded = True
            alias = fallback_alias

        if not alias:
            continue

        norm_al = normalize_alias(alias)
        short_pane = pane_id.split(":", 1)[1] if ":" in pane_id else pane_id
        pane_info = {
            "pane_id": pane_id,
            "short_pane": short_pane,
            "label": str(hp.get("label") or ""),
            "tab_id": hp.get("tab_id"),
            "focused": bool(hp.get("focused", False)),
            "pid": pid,
        }
        result.setdefault(norm_al, []).append(pane_info)

    for al in result:
        result[al].sort(key=lambda p: (not p["focused"], p["pane_id"]))

    return result


# ---------------------------------------------------------------------------
# 4. Smart Auto-Rotation Engine (`compute_smart_auto_choice`)
# ---------------------------------------------------------------------------


def _normalize_target_mode(target_mode: str, active_model: str) -> str:
    tm = (target_mode or "").strip().lower()
    am = (active_model or "").strip().lower()

    if tm in ("claude", "gpt", "3p") or any(k in tm for k in ("claude", "gpt", "3p", "opus", "sonnet", "haiku")):
        return "claude"
    if tm in ("carbon", "ultra") or "carbon" in tm or "ultra" in tm or "carbon" in am:
        return "carbon"
    if (not tm or tm == "auto") and any(k in am for k in ("claude", "gpt", "3p", "opus", "sonnet", "haiku")):
        return "claude"
    return "gemini"


def _filter_busy_panes(raw_panes: list | None, exclude_pane_id: str | None) -> list[dict]:
    if not raw_panes:
        return []
    excl = (exclude_pane_id or "").strip()
    busy: list[dict] = []
    for item in raw_panes:
        if isinstance(item, dict):
            pid_str = str(item.get("pane_id") or "")
            short_str = str(item.get("short_pane") or (pid_str.split(":", 1)[1] if ":" in pid_str else pid_str))
            if excl and (excl == pid_str or excl == short_str):
                continue
            busy.append(dict(item))
        elif isinstance(item, str) and item.strip():
            pid_str = item.strip()
            short_str = pid_str.split(":", 1)[1] if ":" in pid_str else pid_str
            if excl and (excl == pid_str or excl == short_str):
                continue
            busy.append({
                "pane_id": pid_str,
                "short_pane": short_str,
                "label": "",
                "tab_id": None,
                "focused": False,
            })
    return busy


def compute_smart_auto_choice(
    accounts_map: dict[str, dict],
    target_mode: str,
    active_model: str = "",
    active_panes_map: dict[str, list[dict]] | None = None,
    allow_ultra_for_pro_models: bool = False,
    exclude_pane_id: str | None = None,
) -> dict:
    """
    Selects the optimal account across `accounts_map` combining:
      1) Strict `AND` availability (`q5h > 0.001 and qweek > 0.001`)
      2) Automatic `ULTRA` reserve for Carbon when healthy `PRO` accounts (`>=15%`) exist
      3) Anti-Collision penalty/bonus across active Herdr panes (`exclude_pane_id` excluded)
      4) Burn-First priority to drain already-open 5H windows before opening untouched 100% accounts
    """
    norm_mode = _normalize_target_mode(target_mode, active_model)
    fam_key = "claude" if norm_mode == "claude" else "gemini"
    am_low = (active_model or "").lower()
    is_heavy_gemini = any(x in am_low for x in ("argon", "hydrogen", "orchestrator"))
    panes_lookup = active_panes_map or {}
    now_dt = datetime.now(timezone.utc)

    evaluations: list[dict] = []
    available_candidates: list[dict] = []
    exhausted_candidates: list[dict] = []
    valid_ultra_count = 0

    for raw_alias, acc in (accounts_map or {}).items():
        if not isinstance(acc, dict):
            continue
        alias = normalize_alias(raw_alias) or raw_alias
        q = acc.get("quota") if isinstance(acc.get("quota"), dict) else {}

        def _qget(key: str) -> object:
            if key in q and q[key] is not None:
                return q[key]
            return acc.get(key)

        raw_supports_carbon = _qget("supports_carbon")
        raw_plan = _qget("plan_type")
        plan_type = str(raw_plan).upper() if raw_plan else ("ULTRA" if raw_supports_carbon else "FREE")
        supports_carbon = bool(raw_supports_carbon or plan_type == "ULTRA")
        is_ultra = bool(plan_type == "ULTRA" or supports_carbon)
        tier_id = str(_qget("tier_id") or ("g1-ultra-tier" if plan_type == "ULTRA" else ""))

        is_revoked = bool(acc.get("is_revoked", False))
        is_locked = bool(acc.get("locked", False))
        note = str(acc.get("note") or "")
        email = str(acc.get("email") or "")

        raw_panes = panes_lookup.get(alias)
        if raw_panes is None and raw_alias != alias:
            raw_panes = panes_lookup.get(raw_alias)
        busy_panes = _filter_busy_panes(raw_panes, exclude_pane_id)

        q5h, r5h = normalize_window(
            _qget(f"{fam_key}_5h_fraction"),  # type: ignore[arg-type]
            _qget(f"{fam_key}_5h_reset"),  # type: ignore[arg-type]
            now_dt=now_dt,
        )
        qweek, rweek = normalize_window(
            _qget(f"{fam_key}_weekly_fraction"),  # type: ignore[arg-type]
            _qget(f"{fam_key}_weekly_reset"),  # type: ignore[arg-type]
            now_dt=now_dt,
        )
        disabled = bool(_qget(f"{fam_key}_disabled") or False)

        q5h_val = 0.0 if q5h is None else float(q5h)
        qweek_val = 0.0 if qweek is None else float(qweek)
        if qweek_val <= 0.001 or disabled:
            q5h_val = 0.0
            qweek_val = 0.0

        ev: dict = {
            "alias": alias,
            "email": email,
            "plan_type": plan_type,
            "tier_id": tier_id,
            "supports_carbon": supports_carbon,
            "is_ultra": is_ultra,
            "is_revoked": is_revoked,
            "locked": is_locked,
            "note": note,
            "q5h": q5h_val,
            "qweek": qweek_val,
            "r5h": r5h,
            "rweek": rweek,
            "busy_panes": busy_panes,
            "ultra_reserved": False,
            "burn_first": False,
            "eligible": False,
            "available": False,
            "score": None,
            "selected": False,
            "status": "candidate",
            "reason": "",
        }
        evaluations.append(ev)

        if is_revoked:
            ev["status"] = "revoked"
            ev["reason"] = "Token revocado o expirado"
            continue

        if norm_mode == "carbon" and not is_ultra:
            ev["status"] = "not_ultra"
            ev["reason"] = "Gemini 4 Carbon requiere ULTRA"
            continue

        if is_locked:
            ev["status"] = "locked"
            ev["reason"] = f"Reservada ({note})" if note else "Reservada"
            continue

        if is_ultra:
            valid_ultra_count += 1

        ev["eligible"] = True
        if q5h_val > 0.001 and qweek_val > 0.001:
            ev["available"] = True
            available_candidates.append(ev)
        else:
            ev["status"] = "exhausted"
            ev["reason"] = "Semanal agotada" if qweek_val <= 0.001 else "5H agotada"
            exhausted_candidates.append(ev)

    if norm_mode == "carbon" and valid_ultra_count == 0:
        return {
            "best_alias": None,
            "best_score": -1.0,
            "best_5h": 0.0,
            "best_week": 0.0,
            "target_mode": norm_mode,
            "reason": "no_ultra",
            "ultra_reserved_count": 0,
            "earliest_alias": None,
            "min_reset_seconds": None,
            "earliest_reset": None,
            "evaluations": evaluations,
        }

    # Automatic ULTRA reserve when healthy PRO accounts (>=15% in both 5H & Weekly) exist
    ultra_reserved_count = 0
    active_pool = available_candidates
    if norm_mode in ("gemini", "claude") and not allow_ultra_for_pro_models:
        healthy_pro = [
            ev
            for ev in available_candidates
            if not ev["is_ultra"] and ev["q5h"] >= 0.15 and ev["qweek"] >= 0.15
        ]
        if healthy_pro:
            pro_pool = [ev for ev in available_candidates if not ev["is_ultra"]]
            for ev in available_candidates:
                if ev["is_ultra"]:
                    ev["ultra_reserved"] = True
                    ev["eligible"] = False
                    ev["status"] = "ultra_reserved"
                    ev["reason"] = "[Reserva ULTRA protegida para Carbon]"
                    ultra_reserved_count += 1
            active_pool = pro_pool

    best_ev: dict | None = None
    best_score = -1e9

    for ev in active_pool:
        q5h_v = ev["q5h"]
        qweek_v = ev["qweek"]
        busy_n = len(ev["busy_panes"])

        if norm_mode == "carbon":
            score = (qweek_v * 0.70) + (q5h_v * 0.30) + (0.01 if ev["tier_id"] == "g1-ultra-tier" else 0.0)
        elif norm_mode == "claude":
            score = (qweek_v * 0.65) + (q5h_v * 0.35)
        elif is_heavy_gemini:
            score = (qweek_v * 0.55) + (q5h_v * 0.45)
        else:
            score = (q5h_v * 0.60) + (qweek_v * 0.40)

        # Anti-Collision: strongly prefer idle accounts over accounts busy in other Herdr panes
        if busy_n == 0 and q5h_v >= 0.15:
            score += 0.30
        elif busy_n > 0:
            score -= 0.15 * busy_n

        # Burn-First: finish draining an already-opened 5H window before cracking open a fresh 100% account
        if busy_n == 0 and 0.20 <= q5h_v < 0.9995 and qweek_v >= 0.25:
            score += 0.22
            ev["burn_first"] = True

        ev["score"] = round(score, 6)
        if score > best_score:
            best_score = score
            best_ev = ev

    # Compute earliest reset across exhausted eligible accounts
    earliest_alias: str | None = None
    min_reset_seconds: float | None = None
    earliest_reset: str | None = None

    for ev in exhausted_candidates:
        blocking_rst = ev["rweek"] if ev["qweek"] <= 0.001 else ev["r5h"]
        if not blocking_rst:
            continue
        rst_dt = parse_iso_datetime(blocking_rst)
        if rst_dt is None:
            continue
        secs = max(0.0, (rst_dt - now_dt).total_seconds())
        if secs > 0 and (min_reset_seconds is None or secs < min_reset_seconds):
            min_reset_seconds = secs
            earliest_alias = ev["alias"]
            earliest_reset = blocking_rst

    if best_ev is not None:
        best_ev["selected"] = True
        best_ev["status"] = "selected"
        return {
            "best_alias": best_ev["alias"],
            "best_score": round(best_score, 6),
            "best_5h": best_ev["q5h"],
            "best_week": best_ev["qweek"],
            "target_mode": norm_mode,
            "reason": "ok",
            "ultra_reserved_count": ultra_reserved_count,
            "earliest_alias": earliest_alias,
            "min_reset_seconds": min_reset_seconds,
            "earliest_reset": earliest_reset,
            "evaluations": evaluations,
        }

    return {
        "best_alias": None,
        "best_score": -1.0,
        "best_5h": 0.0,
        "best_week": 0.0,
        "target_mode": norm_mode,
        "reason": "quota_exhausted" if exhausted_candidates else "no_accounts",
        "ultra_reserved_count": ultra_reserved_count,
        "earliest_alias": earliest_alias,
        "min_reset_seconds": min_reset_seconds,
        "earliest_reset": earliest_reset,
        "evaluations": evaluations,
    }


__all__ = [
    "ANTIGRAVITY_UA",
    "RESERVED_ALIASES",
    "SAFE_QUOTA_KEYS",
    "resolve_real_home",
    "get_base_dir",
    "get_accounts_dir",
    "get_cache_dir",
    "get_locks_dir",
    "normalize_alias",
    "validate_alias",
    "extract_agy_alias",
    "atomic_write_json",
    "sanitize_account_for_json",
    "parse_iso_datetime",
    "normalize_window",
    "pct_display",
    "default_max_tokens_for_model",
    "estimate_context_from_transcript",
    "scan_active_herdr_panes",
    "compute_smart_auto_choice",
]
