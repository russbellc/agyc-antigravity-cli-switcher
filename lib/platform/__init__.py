"""
Cross-platform OS abstraction layer for agyc (Linux POSIX + Windows Win32).

Designed for <2ms import latency under `python -S`: heavy stdlib modules
(`ctypes`, `subprocess`, `_socket`, `msvcrt`, `pwd`, `fcntl`, `select`, `shutil`,
`json`, `threading`) are strictly deferred inside the functions that need them.
"""

from __future__ import annotations

import os

IS_WINDOWS: bool = os.name == "nt"


def _has_agyc_homes_segment(path: str) -> bool:
    """Returns True if `path` points inside an isolated `.agyc_homes` profile directory."""
    s = (path or "").strip().replace("\\", "/")
    if not s:
        return False
    return "/.agyc_homes/" in s or s.rstrip("/").endswith("/.agyc_homes") or s == ".agyc_homes"


def _strip_agyc_homes(path: str) -> str:
    """Strips any `/.agyc_homes/...` or `\\.agyc_homes\\...` suffix while preserving root."""
    s = (path or "").strip()
    if not s:
        return ""
    norm = s.replace("\\", "/")
    idx = norm.find("/.agyc_homes/")
    if idx != -1:
        s = s[:idx]
    else:
        norm_no_trail = norm.rstrip("/")
        if norm_no_trail.endswith("/.agyc_homes"):
            cut = len(norm_no_trail) - len("/.agyc_homes")
            s = s[:cut]
    if len(s) == 3 and s[1] == ":" and s[2] in ("/", "\\"):
        return s
    stripped = s.rstrip("/\\")
    if not stripped:
        return "/" if s.startswith("/") else s
    if len(stripped) == 2 and stripped[1] == ":":
        return stripped + os.sep
    return stripped


def _normalize_alias_token(alias: str) -> str:
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


def _extract_agy_alias_token(text: str) -> str | None:
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


def _is_safe_alias_token(s: str) -> bool:
    if not s or len(s) > 32 or ".." in s or "/" in s or "\\" in s or "\x00" in s:
        return False
    if not (s[0].isascii() and s[0].isalnum()):
        return False
    for ch in s:
        if not ((ch.isascii() and ch.isalnum()) or ch in ("_", "-")):
            return False
    return True


def _extract_alias_from_home_path(path_val: str) -> str | None:
    if not path_val:
        return None
    norm = path_val.replace("\\", "/")
    marker = "/.agyc_homes/"
    idx = norm.find(marker)
    if idx != -1:
        rest = norm[idx + len(marker) :]
        seg = rest.split("/", 1)[0].strip()
        if _is_safe_alias_token(seg):
            return _normalize_alias_token(seg)
    return _extract_agy_alias_token(path_val)


if IS_WINDOWS:
    from .win32 import (
        acquire_file_lock,
        create_dir_link,
        create_file_link,
        default_herdr_socket_path,
        ensure_private_dir,
        ensure_private_file,
        find_ancestor_agy_pid,
        get_base_dir,
        get_cache_dir,
        get_locks_dir,
        get_run_dir,
        harden_ntfs_acl,
        is_dir_link,
        query_herdr_ipc,
        read_dir_link,
        read_stdin_nonblocking,
        resolve_real_home,
        scan_agy_processes,
        send_low_quota_toast,
        spawn_detached,
    )
else:
    from .linux import (
        acquire_file_lock,
        create_dir_link,
        create_file_link,
        default_herdr_socket_path,
        ensure_private_dir,
        ensure_private_file,
        find_ancestor_agy_pid,
        get_base_dir,
        get_cache_dir,
        get_locks_dir,
        get_run_dir,
        harden_ntfs_acl,
        is_dir_link,
        query_herdr_ipc,
        read_dir_link,
        read_stdin_nonblocking,
        resolve_real_home,
        scan_agy_processes,
        send_low_quota_toast,
        spawn_detached,
    )


__all__ = [
    "IS_WINDOWS",
    "resolve_real_home",
    "get_base_dir",
    "get_cache_dir",
    "get_locks_dir",
    "get_run_dir",
    "ensure_private_dir",
    "ensure_private_file",
    "harden_ntfs_acl",
    "create_dir_link",
    "is_dir_link",
    "read_dir_link",
    "create_file_link",
    "acquire_file_lock",
    "default_herdr_socket_path",
    "query_herdr_ipc",
    "scan_agy_processes",
    "find_ancestor_agy_pid",
    "read_stdin_nonblocking",
    "spawn_detached",
    "send_low_quota_toast",
]
