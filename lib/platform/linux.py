"""Linux / POSIX backend for `lib.platform`."""

from __future__ import annotations

import os

from . import (
    _extract_alias_from_home_path,
    _has_agyc_homes_segment,
    _is_safe_alias_token,
    _normalize_alias_token,
    _strip_agyc_homes,
)


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


def ensure_private_dir(path: str, mode: int = 0o700) -> str:
    """Creates `path` recursively and enforces POSIX directory permissions."""
    os.makedirs(path, mode=mode, exist_ok=True)
    try:
        os.chmod(path, mode)
    except OSError:
        pass
    return path


def ensure_private_file(path: str, mode: int = 0o600) -> str:
    """Ensures `path` exists with strict POSIX file permissions (`0600`)."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        ensure_private_dir(parent, 0o700)
    if not os.path.exists(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT, mode)
        os.close(fd)
    try:
        os.chmod(path, mode)
    except OSError:
        pass
    return path


def harden_ntfs_acl(path: str) -> bool:
    """POSIX stub: permissions are handled via standard POSIX mode bits."""
    return os.path.exists(path)


def get_base_dir(real_home: str | None = None) -> str:
    """Returns Antigravity CLI base directory (`~/.gemini/antigravity-cli` or snap)."""
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
    return ensure_private_dir(default_path, 0o700)


def get_cache_dir(real_home: str | None = None) -> str:
    """Returns `~/.cache/agyc` with strict `0700` permissions."""
    rh = _strip_agyc_homes(real_home) if real_home else resolve_real_home()
    return ensure_private_dir(os.path.join(rh, ".cache", "agyc"), 0o700)


def get_locks_dir(real_home: str | None = None) -> str:
    """Returns `~/.cache/agyc/locks` with strict `0700` permissions."""
    return ensure_private_dir(os.path.join(get_cache_dir(real_home), "locks"), 0o700)


def get_run_dir(real_home: str | None = None) -> str:
    """Returns `~/.cache/agyc/run` with strict `0700` permissions."""
    return ensure_private_dir(os.path.join(get_cache_dir(real_home), "run"), 0o700)


def create_dir_link(src: str, dst: str) -> None:
    """Creates a POSIX symlink from `dst` -> `src`."""
    parent = os.path.dirname(os.path.abspath(dst))
    if parent:
        os.makedirs(parent, exist_ok=True)
    os.symlink(src, dst)


def is_dir_link(path: str) -> bool:
    """Returns True if `path` is a symlink."""
    return os.path.islink(path)


def read_dir_link(path: str) -> str:
    """Returns the target path of a symlink."""
    return os.readlink(path)


def create_file_link(src: str, dst: str) -> None:
    """Creates a POSIX symlink for a file (`dst` -> `src`)."""
    parent = os.path.dirname(os.path.abspath(dst))
    if parent:
        os.makedirs(parent, exist_ok=True)
    os.symlink(src, dst)


class _PosixFileLock:
    """Advisory flock wrapper supporting both `.release()` and context manager."""

    def __init__(self, fd: int) -> None:
        self._fd: int | None = fd

    def release(self) -> None:
        if self._fd is None:
            return
        fd = self._fd
        self._fd = None
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass

    def __enter__(self) -> "_PosixFileLock":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.release()


def acquire_file_lock(lock_path: str, blocking: bool = True) -> _PosixFileLock:
    """Acquires an advisory `fcntl.flock` lock on `lock_path`."""
    import fcntl

    parent = os.path.dirname(os.path.abspath(lock_path))
    if parent:
        ensure_private_dir(parent, 0o700)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            os.chmod(lock_path, 0o600)
        except OSError:
            pass
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        fcntl.flock(fd, flags)
        return _PosixFileLock(fd)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def default_herdr_socket_path(real_home: str | None = None) -> str:
    """Resolves default Herdr UNIX socket path."""
    rh = _strip_agyc_homes(real_home) if real_home else resolve_real_home()
    return os.environ.get("HERDR_SOCKET_PATH") or os.path.join(rh, ".config", "herdr", "herdr.sock")


def query_herdr_ipc(
    sock_path: str | None,
    payload_dict: dict,
    timeout: float = 0.06,
) -> dict | None:
    """Queries Herdr over an AF_UNIX socket using JSON-line IPC."""
    import _socket
    import json

    target = sock_path if sock_path else default_herdr_socket_path()
    if not target or not os.path.exists(target):
        return None

    s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(target)
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
    try:
        with open(os.path.join(proc_dir, "stat"), "rb") as sf:
            data = sf.read(128)
        rparen = data.rfind(b")")
        if rparen != -1 and rparen + 3 <= len(data):
            return data[rparen + 2 : rparen + 3] or b"S"
    except OSError:
        pass
    return b"S"


def scan_agy_processes(proc_root: str = "/proc", run_dir: str | None = None) -> list[dict]:
    """Scans `proc_root` for live `agy-real` / ELF `agy` processes owned by current UID."""
    del run_dir  # Linux reads live /proc directly
    results: list[dict] = []
    uid = os.getuid()

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
                        pane_id = item[14:].decode("utf-8", errors="ignore").strip() or None
                    elif item.startswith((b"HOME=", b"ANTIGRAVITY_APP_DATA_DIR=")):
                        val = item.split(b"=", 1)[1].decode("utf-8", errors="ignore")
                        cand = _extract_alias_from_home_path(val)
                        if cand:
                            env_alias = cand
                    elif item.startswith((b"AGYC_ACCOUNT=", b"AGYC_ALIAS=")) and not env_alias:
                        val = item.split(b"=", 1)[1].decode("utf-8", errors="ignore").strip()
                        if _is_safe_alias_token(val):
                            env_alias = _normalize_alias_token(val)

                results.append({
                    "pid": int(name),
                    "exe_name": comm.decode("utf-8", errors="ignore"),
                    "alias": env_alias,
                    "herdr_pane_id": pane_id,
                    "is_running": state not in (b"T", b"t"),
                })
    except OSError:
        return []

    return results


def find_ancestor_agy_pid(start_pid: int | None = None, max_hops: int = 8) -> int | None:
    """Climbs `/proc/<pid>` parent chain to locate an ancestor `agy` CLI process."""
    pid = start_pid if start_pid is not None else os.getppid()
    for _ in range(max_hops):
        if not pid or pid <= 1:
            break
        cmd_file = f"/proc/{pid}/cmdline"
        if os.path.exists(cmd_file):
            try:
                with open(cmd_file, "rb") as f:
                    cmd = f.read().decode("utf-8", errors="ignore")
                if "agy" in cmd and "statusline" not in cmd and "titleline" not in cmd and "topbar" not in cmd:
                    return pid
            except OSError:
                pass
        status_file = f"/proc/{pid}/status"
        if not os.path.exists(status_file):
            break
        ppid = None
        try:
            with open(status_file, "r", encoding="utf-8", errors="ignore") as sf:
                for line in sf:
                    if line.startswith("PPid:"):
                        ppid = int(line.split()[1])
                        break
        except (OSError, ValueError, IndexError):
            break
        if not ppid or ppid <= 1 or ppid == pid:
            break
        pid = ppid
    return None


def read_stdin_nonblocking(max_wait_sec: float = 0.020, *, fd: int | None = None) -> bytes:
    """Reads available stdin bytes using non-blocking `os.read` + `select.select`."""
    import select
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

    prev_blocking: bool | None = None
    try:
        prev_blocking = os.get_blocking(fd)
    except OSError:
        pass

    try:
        os.set_blocking(fd, False)
    except OSError:
        pass

    deadline = time.monotonic() + max(0.0, float(max_wait_sec))
    chunks: list[bytes] = []
    try:
        while True:
            rem = deadline - time.monotonic()
            if rem <= 0 and chunks:
                break
            timeout = min(max(0.0, rem), 0.005)
            r, _, _ = select.select([fd], [], [], timeout)
            if not r:
                if rem <= 0:
                    break
                continue
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                if rem <= 0:
                    break
                continue
            except OSError:
                break
            if not chunk:
                break
            chunks.append(chunk)
    except OSError:
        pass
    finally:
        if prev_blocking is not None:
            try:
                os.set_blocking(fd, prev_blocking)
            except OSError:
                pass

    return b"".join(chunks)


def spawn_detached(cmd: list[str] | tuple[str, ...], env: dict[str, str] | None = None):
    """Spawns a detached background process in a new POSIX session."""
    import subprocess

    return subprocess.Popen(
        list(cmd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
        env=env,
    )


def send_low_quota_toast(title: str, body: str, herdr_bin: str | None = None) -> bool:
    """Dispatches a non-blocking Herdr toast notification on Linux."""
    import shutil

    cmd_path: str | None = None
    if herdr_bin:
        cmd_path = herdr_bin if os.path.isfile(herdr_bin) else shutil.which(herdr_bin)
    else:
        cmd_path = shutil.which("herdr")

    if not cmd_path:
        return False

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
        return False
