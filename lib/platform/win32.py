"""Windows / Win32 backend for `lib.platform`."""

from __future__ import annotations

import os

from . import (
    _extract_alias_from_home_path,
    _has_agyc_homes_segment,
    _is_safe_alias_token,
    _normalize_alias_token,
    _strip_agyc_homes,
)

_CREATE_NEW_PROCESS_GROUP = 0x00000200
_DETACHED_PROCESS = 0x00000008
_CREATE_NO_WINDOW = 0x08000000


def _norm_win_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def resolve_real_home() -> str:
    """Resolves real Windows user profile home ignoring `\\.agyc_homes\\` segments."""
    candidates: list[str] = []
    for env_key in ("AGYC_REAL_HOME", "REAL_HOME", "USERPROFILE"):
        val = os.environ.get(env_key, "").strip()
        if val:
            candidates.append(val)
    try:
        exp = os.path.expanduser("~")
        if exp:
            candidates.append(exp)
    except Exception:
        pass
    home_env = os.environ.get("HOME", "").strip()
    if home_env:
        candidates.append(home_env)

    for raw in candidates:
        if raw == "~":
            continue
        cleaned = _strip_agyc_homes(raw)
        if cleaned and os.path.isdir(cleaned):
            return cleaned

    return os.environ.get("SystemDrive", "C:") + os.sep


def ensure_private_dir(path: str, mode: int = 0o700) -> str:
    """Creates `path` recursively without failing on POSIX permission bits."""
    del mode  # Windows ignores POSIX mode bits; explicit hardening uses harden_ntfs_acl
    os.makedirs(path, exist_ok=True)
    return path


def ensure_private_file(path: str, mode: int = 0o600) -> str:
    """Ensures `path` exists on Windows without relying on POSIX mode bits."""
    del mode
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    if not os.path.exists(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
        os.close(fd)
    return path


def harden_ntfs_acl(path: str) -> bool:
    """Restricts NTFS ACL on `path` exclusively to the current user SID via `icacls`."""
    if not path or not os.path.exists(path):
        return False
    import subprocess

    try:
        who = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
            timeout=5,
        )
        if who.returncode != 0:
            return False
        who_out = who.stdout.decode("utf-8", errors="replace").strip()
        sid = who_out.splitlines()[-1].split(",")[-1].strip().strip('"')
        if not sid.startswith("S-"):
            return False
        grant_arg = f"*{sid}:(OI)(CI)F" if os.path.isdir(path) else f"*{sid}:F"
        res = subprocess.run(
            ["icacls", path, "/inheritance:r", "/grant:r", grant_arg],
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
            timeout=5,
        )
        return res.returncode == 0
    except Exception:
        return False


def get_base_dir(real_home: str | None = None) -> str:
    """Returns Antigravity CLI base directory (`%USERPROFILE%\\.gemini\\antigravity-cli`)."""
    rh = _strip_agyc_homes(real_home) if real_home else resolve_real_home()
    candidates: list[str | None] = []
    if real_home is None:
        candidates.append(os.environ.get("ANTIGRAVITY_HOME"))
        candidates.append(os.environ.get("AGY_CONFIG_DIR"))
    candidates.append(os.path.join(rh, ".gemini", "antigravity-cli"))

    for cand in candidates:
        if cand and not _has_agyc_homes_segment(cand) and os.path.exists(cand):
            return _strip_agyc_homes(cand)

    default_path = os.path.join(rh, ".gemini", "antigravity-cli")
    return ensure_private_dir(default_path, 0o700)


def _is_isolated_home_override(rh_norm: str, up_norm: str) -> bool:
    """True when `AGYC_REAL_HOME`/`REAL_HOME`/`HOME` explicitly redirects away from `USERPROFILE`."""
    for env_key in ("AGYC_REAL_HOME", "REAL_HOME"):
        val = os.environ.get(env_key, "").strip()
        if val:
            cleaned = _strip_agyc_homes(val)
            if cleaned and _norm_win_path(cleaned) != up_norm:
                return True
    home_env = os.environ.get("HOME", "").strip()
    if home_env and home_env != "~":
        cleaned_h = _strip_agyc_homes(home_env)
        if cleaned_h and os.path.isdir(cleaned_h) and _norm_win_path(cleaned_h) != up_norm:
            return True
    return rh_norm != up_norm


def get_cache_dir(real_home: str | None = None) -> str:
    """
    Returns Windows cache directory (`%LOCALAPPDATA%\\agyc\\cache`), falling back to
    `<real_home>\\.cache\\agyc` for hermetic tests or when `LOCALAPPDATA` is unset.
    Respects `AGYC_CACHE_DIR` when explicitly provided.
    """
    env_cache = os.environ.get("AGYC_CACHE_DIR", "").strip()
    if env_cache and not _has_agyc_homes_segment(env_cache):
        if real_home is None or _norm_win_path(_strip_agyc_homes(real_home)) == _norm_win_path(resolve_real_home()):
            return ensure_private_dir(env_cache, 0o700)

    rh = _strip_agyc_homes(real_home) if real_home else resolve_real_home()
    rh_norm = _norm_win_path(rh)
    local_app = os.environ.get("LOCALAPPDATA", "").strip()
    up = os.environ.get("USERPROFILE", "").strip()

    if local_app and not _has_agyc_homes_segment(local_app):
        la_norm = _norm_win_path(local_app)
        if la_norm.startswith(rh_norm.rstrip("\\/") + os.sep) or la_norm == rh_norm:
            return ensure_private_dir(os.path.join(local_app, "agyc", "cache"), 0o700)
        if up:
            up_norm = _norm_win_path(up)
            if rh_norm == up_norm and not _is_isolated_home_override(rh_norm, up_norm):
                return ensure_private_dir(os.path.join(local_app, "agyc", "cache"), 0o700)

    return ensure_private_dir(os.path.join(rh, ".cache", "agyc"), 0o700)


def get_locks_dir(real_home: str | None = None) -> str:
    """Returns `<cache_dir>\\locks`."""
    return ensure_private_dir(os.path.join(get_cache_dir(real_home), "locks"), 0o700)


def get_run_dir(real_home: str | None = None) -> str:
    """Returns `<cache_dir>\\run`."""
    return ensure_private_dir(os.path.join(get_cache_dir(real_home), "run"), 0o700)


def create_dir_link(src: str, dst: str) -> None:
    """Creates an NTFS directory junction (`dst` -> `src`) without requiring Admin rights."""
    if os.path.lexists(dst) or is_dir_link(dst):
        raise FileExistsError(f"Destination already exists: {dst}")

    dst_abs = os.path.abspath(dst)
    src_abs = os.path.abspath(src)
    parent = os.path.dirname(dst_abs)
    if parent:
        os.makedirs(parent, exist_ok=True)

    import subprocess

    res = subprocess.run(
        ["cmd", "/c", "mklink", "/J", dst_abs, src_abs],
        capture_output=True,
        creationflags=_CREATE_NO_WINDOW,
    )
    if res.returncode != 0:
        err_txt = res.stderr.decode("oem", errors="replace").strip() if res.stderr else ""
        out_txt = res.stdout.decode("oem", errors="replace").strip() if res.stdout else ""
        msg = err_txt or out_txt or f"mklink /J failed ({res.returncode})"
        raise OSError(msg)


def is_dir_link(path: str) -> bool:
    """Detects NTFS junctions and directory symlinks cleanly on Python 3.10+."""
    if not path:
        return False

    is_junc = getattr(os.path, "isjunction", None)
    if is_junc is not None:
        try:
            if is_junc(path):
                return True
        except OSError:
            pass

    if os.path.islink(path):
        try:
            if os.path.isdir(path):
                return True
        except OSError:
            pass

    import ctypes

    invalid_attrs = 0xFFFFFFFF
    attr_dir = 0x10
    attr_reparse = 0x400
    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    if attrs == invalid_attrs:
        return False
    if (attrs & attr_dir) and (attrs & attr_reparse):
        try:
            os.readlink(path)
            return True
        except OSError:
            return False
    return False


def read_dir_link(path: str) -> str:
    """Reads an NTFS junction or directory symlink target, stripping `\\\\?\\` prefix."""
    target = os.readlink(path)
    if target.startswith("\\\\?\\UNC\\"):
        return "\\\\" + target[8:]
    if target.startswith("\\\\?\\"):
        return target[4:]
    return target


def create_file_link(src: str, dst: str) -> None:
    """Creates an NTFS hardlink (`os.link`) when possible, falling back to `shutil.copy2`."""
    import shutil

    parent = os.path.dirname(os.path.abspath(dst))
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        os.link(src, dst)
        return
    except OSError:
        pass
    try:
        if os.path.exists(dst) and os.path.samefile(src, dst):
            return
    except OSError:
        pass
    shutil.copy2(src, dst)


class _Win32FileLock:
    """Advisory byte-range `msvcrt.locking` lock supporting `.release()` and `with`."""

    def __init__(self, fd: int) -> None:
        self._fd: int | None = fd

    def release(self) -> None:
        if self._fd is None:
            return
        fd = self._fd
        self._fd = None
        try:
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass

    def __enter__(self) -> "_Win32FileLock":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.release()


def acquire_file_lock(lock_path: str, blocking: bool = True) -> _Win32FileLock:
    """Acquires an exclusive byte-0 file lock using `msvcrt.locking`."""
    import errno
    import msvcrt

    parent = os.path.dirname(os.path.abspath(lock_path))
    if parent:
        ensure_private_dir(parent, 0o700)

    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if os.fstat(fd).st_size == 0:
            try:
                os.write(fd, b"\0")
            except OSError:
                pass
        os.lseek(fd, 0, os.SEEK_SET)
        mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
        try:
            msvcrt.locking(fd, mode, 1)
        except OSError as exc:
            if not blocking and getattr(exc, "errno", None) in (
                errno.EACCES,
                errno.EAGAIN,
                errno.EDEADLK,
                13,
                36,
            ):
                raise BlockingIOError(errno.EAGAIN, str(exc)) from exc
            raise
        return _Win32FileLock(fd)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def default_herdr_socket_path(real_home: str | None = None) -> str:
    """Resolves Herdr IPC endpoint file (`%APPDATA%\\herdr\\herdr.sock` or `.config/herdr/herdr.sock`)."""
    env_sock = os.environ.get("HERDR_SOCKET_PATH", "").strip()
    if env_sock:
        return env_sock

    rh = _strip_agyc_homes(real_home) if real_home else resolve_real_home()
    cfg_sock = os.path.join(rh, ".config", "herdr", "herdr.sock")
    if os.path.isfile(cfg_sock):
        return cfg_sock

    appdata = os.environ.get("APPDATA", "").strip()
    up = os.environ.get("USERPROFILE", "").strip()
    if appdata and not _has_agyc_homes_segment(appdata):
        rh_norm = _norm_win_path(rh)
        ad_norm = _norm_win_path(appdata)
        if ad_norm.startswith(rh_norm.rstrip("\\/") + os.sep) or (
            up and rh_norm == _norm_win_path(up) and not _is_isolated_home_override(rh_norm, _norm_win_path(up))
        ):
            return os.path.join(appdata, "herdr", "herdr.sock")

    return cfg_sock


def _parse_herdr_tcp_port(raw_text: str) -> int | None:
    first_line = (raw_text or "").strip().splitlines()[0].strip() if raw_text and raw_text.strip() else ""
    if not first_line:
        return None
    parts = [p.strip() for p in first_line.split(":")]
    port_str: str | None = None
    if parts[0].isdigit():
        port_str = parts[0]
    elif len(parts) >= 2 and parts[0] in ("127.0.0.1", "localhost") and parts[1].isdigit():
        port_str = parts[1]
    if not port_str:
        return None
    port = int(port_str)
    return port if 1 <= port <= 65535 else None


def _query_herdr_named_pipe(pipe_name: str, payload_dict: dict, timeout: float) -> tuple[bool, dict | None]:
    """Queries a Windows Named Pipe speaking newline-delimited JSON-RPC.
    Returns `(pipe_existed, decoded_dict_or_none)`.
    """
    import ctypes
    from ctypes import wintypes
    import json
    import time

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
    k32.WaitNamedPipeW.restype = wintypes.BOOL
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.WriteFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    k32.WriteFile.restype = wintypes.BOOL
    k32.PeekNamedPipe.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
    ]
    k32.PeekNamedPipe.restype = wintypes.BOOL
    k32.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    k32.ReadFile.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    invalid_handle = wintypes.HANDLE(-1).value
    timeout_ms = max(1, int(float(timeout) * 1000))
    if not k32.WaitNamedPipeW(pipe_name, timeout_ms):
        err = ctypes.get_last_error()
        if err in (2, 3):  # ERROR_FILE_NOT_FOUND / ERROR_PATH_NOT_FOUND
            return False, None
        return True, None

    handle = k32.CreateFileW(pipe_name, 0xC0000000, 0, None, 3, 0, None)
    if handle == invalid_handle:
        err = ctypes.get_last_error()
        if err in (2, 3):
            return False, None
        return True, None

    try:
        raw_req = (json.dumps(payload_dict, ensure_ascii=False) + "\n").encode("utf-8")
        written = wintypes.DWORD(0)
        buf_in = ctypes.create_string_buffer(raw_req, len(raw_req))
        if not k32.WriteFile(handle, buf_in, len(raw_req), ctypes.byref(written), None):
            return True, None

        deadline = time.monotonic() + max(0.01, float(timeout))
        chunks: list[bytes] = []
        avail = wintypes.DWORD(0)
        read_n = wintypes.DWORD(0)
        while time.monotonic() < deadline:
            avail.value = 0
            if not k32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None):
                if ctypes.get_last_error() == 109:  # ERROR_BROKEN_PIPE
                    break
                break
            if avail.value > 0:
                to_read = min(65536, int(avail.value))
                buf_out = ctypes.create_string_buffer(to_read)
                read_n.value = 0
                if not k32.ReadFile(handle, buf_out, to_read, ctypes.byref(read_n), None) or read_n.value == 0:
                    break
                chunk = buf_out.raw[: int(read_n.value)]
                chunks.append(chunk)
                if b"\n" in chunk:
                    break
            else:
                time.sleep(0.002)

        raw_line = b"".join(chunks).split(b"\n", 1)[0]
        if not raw_line:
            return True, None
        resp = json.loads(raw_line.decode("utf-8", errors="replace"))
        return True, (resp if isinstance(resp, dict) else None)
    except Exception:
        return True, None
    finally:
        k32.CloseHandle(handle)


def query_herdr_ipc(
    sock_path: str | None,
    payload_dict: dict,
    timeout: float = 0.06,
) -> dict | None:
    """Queries Herdr over Windows Named Pipe (`\\\\.\\pipe\\<sock_path>`), with TCP fallback."""
    import _socket
    import json

    target = sock_path
    if not target:
        env_sock = os.environ.get("HERDR_SOCKET_PATH", "").strip()
        if env_sock:
            target = env_sock
        else:
            appdata = os.environ.get("APPDATA", "").strip()
            ad_sock = os.path.join(appdata, "herdr", "herdr.sock") if appdata else ""
            target = ad_sock if (ad_sock and os.path.isfile(ad_sock)) else default_herdr_socket_path()

    if not target:
        return None

    is_explicit_pipe = target.startswith("\\\\.\\pipe\\")
    pipe_name = target if is_explicit_pipe else "\\\\.\\pipe\\" + os.path.abspath(target)
    pipe_existed, pipe_resp = _query_herdr_named_pipe(pipe_name, payload_dict, timeout)
    if pipe_existed:
        return pipe_resp

    if is_explicit_pipe or not os.path.isfile(target):
        return None

    try:
        with open(target, "r", encoding="utf-8", errors="ignore") as sf:
            raw_text = sf.read(256)
    except OSError:
        return None

    port = _parse_herdr_tcp_port(raw_text)
    if port is None:
        return None

    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        raw_req = (json.dumps(payload_dict, ensure_ascii=False) + "\n").encode("utf-8")
        s.sendall(raw_req)
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
            return None
        resp = json.loads(raw_line.decode("utf-8", errors="replace"))
        return resp if isinstance(resp, dict) else None
    except Exception:
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass


def _list_win32_processes_with_ppid() -> dict[int, tuple[str, int]]:
    """Enumerates active Windows PIDs -> `(executable filename, parent PID)` via `CreateToolhelp32Snapshot`."""
    import ctypes
    from ctypes import wintypes

    th32cs_snapprocess = 0x00000002
    invalid_handle = wintypes.HANDLE(-1).value
    max_path = 260

    class _PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * max_path),
        ]

    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
    k32.Process32FirstW.restype = wintypes.BOOL
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
    k32.Process32NextW.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    snap = k32.CreateToolhelp32Snapshot(th32cs_snapprocess, 0)
    if snap == invalid_handle:
        return {}

    procs: dict[int, tuple[str, int]] = {}
    try:
        pe = _PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            procs[int(pe.th32ProcessID)] = (str(pe.szExeFile), int(pe.th32ParentProcessID))
            ok = k32.Process32NextW(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)
    return procs


def _list_win32_processes() -> dict[int, str]:
    """Enumerates active Windows PIDs -> executable filename via `CreateToolhelp32Snapshot`."""
    return {pid: exe for pid, (exe, _) in _list_win32_processes_with_ppid().items()}


def find_ancestor_agy_pid(start_pid: int | None = None, max_hops: int = 8) -> int | None:
    """Climbs Windows `th32ParentProcessID` chain to locate an ancestor `agy.exe` / `agy-real.exe`."""
    procs = _list_win32_processes_with_ppid()
    if not procs:
        return None
    cur = start_pid if start_pid is not None else os.getpid()
    seen: set[int] = set()
    for _ in range(max_hops):
        if not cur or cur in seen:
            break
        seen.add(cur)
        entry = procs.get(cur)
        if not entry:
            break
        exe, ppid = entry
        if cur != (start_pid if start_pid is not None else os.getpid()):
            if exe.lower() in ("agy-real.exe", "agy.exe", "antigravity.exe"):
                return cur
        if not ppid or ppid == cur:
            break
        cur = ppid
    return None


def scan_agy_processes(proc_root: str = "/proc", run_dir: str | None = None) -> list[dict]:
    """
    Enumerates live `agy-real.exe` / `agy.exe` processes via `CreateToolhelp32Snapshot`
    and cross-references `<pid>.json` state files in `run_dir`, purging dead PID files.
    """
    del proc_root  # Unused on Windows
    import json

    target_run_dir = run_dir if run_dir is not None else os.path.join(get_cache_dir(), "run")
    all_procs = _list_win32_processes()
    agy_procs = {
        pid: exe
        for pid, exe in all_procs.items()
        if exe.lower() in ("agy-real.exe", "agy.exe", "antigravity.exe")
    }

    meta_by_pid: dict[int, dict] = {}
    if target_run_dir and os.path.isdir(target_run_dir):
        try:
            with os.scandir(target_run_dir) as it:
                for entry in it:
                    name = entry.name
                    if not name.endswith(".json"):
                        continue
                    stem = name[:-5]
                    if not stem.isdigit():
                        continue
                    pid = int(stem)
                    if pid not in agy_procs:
                        try:
                            os.unlink(entry.path)
                        except OSError:
                            pass
                        continue
                    try:
                        with open(entry.path, "r", encoding="utf-8") as mf:
                            data = json.load(mf)
                        if isinstance(data, dict):
                            meta_by_pid[pid] = data
                    except Exception:
                        pass
        except OSError:
            pass

    results: list[dict] = []
    for pid, exe_name in agy_procs.items():
        meta = meta_by_pid.get(pid) or {}
        alias: str | None = None
        for home_key in ("home", "HOME", "antigravity_app_data_dir", "ANTIGRAVITY_APP_DATA_DIR"):
            hval = meta.get(home_key)
            if isinstance(hval, str) and hval.strip():
                alias = _extract_alias_from_home_path(hval)
                if alias:
                    break
        if not alias:
            raw_alias = meta.get("alias") or meta.get("account")
            if isinstance(raw_alias, str) and _is_safe_alias_token(raw_alias.strip()):
                alias = _normalize_alias_token(raw_alias.strip())

        raw_pane = meta.get("herdr_pane_id") or meta.get("pane_id")
        pane_id = raw_pane.strip() if isinstance(raw_pane, str) and raw_pane.strip() else None

        results.append({
            "pid": pid,
            "exe_name": exe_name,
            "alias": alias,
            "herdr_pane_id": pane_id,
            "is_running": True,
        })

    return results


def _read_fd_via_thread(fd: int, max_wait_sec: float) -> bytes:
    import threading

    chunks: list[bytes] = []

    def _worker() -> None:
        try:
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
        except OSError:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=max(0.0, float(max_wait_sec)))
    return b"".join(chunks)


def read_stdin_nonblocking(max_wait_sec: float = 0.020, *, fd: int | None = None) -> bytes:
    """Reads available stdin bytes using Win32 `PeekNamedPipe` with thread fallback."""
    import ctypes
    from ctypes import wintypes
    import msvcrt
    import sys
    import time

    if fd is None:
        try:
            if sys.stdin is not None and sys.stdin.isatty():
                return b""
            fd = sys.stdin.fileno() if sys.stdin is not None else 0
        except Exception:
            fd = 0

    try:
        if os.isatty(fd):
            return b""
    except OSError:
        pass

    try:
        handle = msvcrt.get_osfhandle(fd)
    except OSError:
        return b""

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.PeekNamedPipe.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
    ]
    k32.PeekNamedPipe.restype = wintypes.BOOL

    error_broken_pipe = 109
    deadline = time.monotonic() + max(0.0, float(max_wait_sec))
    chunks: list[bytes] = []

    while True:
        avail = wintypes.DWORD(0)
        ok = k32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None)
        if not ok:
            err = ctypes.get_last_error()
            if err == error_broken_pipe:
                break
            if not chunks:
                return _read_fd_via_thread(fd, max(0.0, deadline - time.monotonic()))
            break

        if avail.value > 0:
            to_read = min(65536, int(avail.value))
            try:
                chunk = os.read(fd, to_read)
            except OSError:
                break
            if not chunk:
                break
            chunks.append(chunk)
            continue

        rem = deadline - time.monotonic()
        if rem <= 0:
            break
        time.sleep(min(rem, 0.002))

    return b"".join(chunks)


def spawn_detached(cmd: list[str] | tuple[str, ...], env: dict[str, str] | None = None):
    """Spawns a detached background process on Windows (`CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`)."""
    import subprocess

    return subprocess.Popen(
        list(cmd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_CREATE_NEW_PROCESS_GROUP | _DETACHED_PROCESS,
        close_fds=True,
        env=env,
    )


def send_low_quota_toast(title: str, body: str, herdr_bin: str | None = None) -> bool:
    """Sends a detached toast via `herdr.exe` if present, else PowerShell `NotifyIcon`."""
    import shutil

    cmd_path: str | None = None
    if herdr_bin:
        cmd_path = herdr_bin if os.path.isfile(herdr_bin) else shutil.which(herdr_bin)
    else:
        cmd_path = shutil.which("herdr.exe") or shutil.which("herdr")

    if cmd_path:
        try:
            spawn_detached([
                cmd_path,
                "notification",
                "show",
                "--position",
                "top-right",
                "--sound",
                "none",
                "--body",
                body,
                title,
            ])
            return True
        except OSError:
            pass

    ps_bin = shutil.which("powershell.exe") or shutil.which("powershell")
    if not ps_bin:
        return False

    ps_script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Warning; "
        "$n.BalloonTipTitle = $env:AGYC_TOAST_TITLE; "
        "$n.BalloonTipText = $env:AGYC_TOAST_BODY; "
        "$n.Visible = $true; "
        "$n.ShowBalloonTip(5000); "
        "Start-Sleep -Milliseconds 5200; "
        "$n.Dispose()"
    )
    env = os.environ.copy()
    env["AGYC_TOAST_TITLE"] = str(title or "")
    env["AGYC_TOAST_BODY"] = str(body or "")
    try:
        spawn_detached(
            [
                ps_bin,
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                ps_script,
            ],
            env=env,
        )
        return True
    except OSError:
        return False
