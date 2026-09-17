"""Private, atomic announcement operation state."""

import fcntl
import json
import os
import stat
import time
from contextlib import contextmanager
from pathlib import Path


class StateError(Exception):
    pass


def state_home():
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))


def feature_root():
    return state_home() / "pkg" / "announcements"


def _absolute_components(path):
    path = Path(path).absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        yield current


def _safe_directory(path, *, owner=False, private=False):
    try:
        info = Path(path).lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise StateError("announcement state path has an unsafe ancestor")
    if owner and info.st_uid != os.getuid():
        raise StateError("announcement state path has a different owner")
    if private and info.st_mode & 0o077:
        raise StateError("announcement feature state directory is not private")
    return True


def _validate_base_read():
    home = state_home().absolute()
    for component in _absolute_components(home):
        if not _safe_directory(component, owner=component == home):
            return False
    pkg = home / "pkg"
    if not _safe_directory(pkg, owner=True):
        return False
    root = pkg / "announcements"
    if not _safe_directory(root, owner=True, private=True):
        return False
    return True


def feature_root_available():
    """Validate the existing feature root without creating or chmodding it."""
    return _validate_base_read()


def validate_read_parent(path):
    path = Path(path).absolute()
    root = feature_root().absolute()
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise StateError("announcement state path escaped its feature root") from None
    if not _validate_base_read():
        return False
    current = root
    for part in relative.parts:
        current /= part
        if not _safe_directory(current, owner=True, private=True):
            return False
    return True


def _mkdir_checked(path, *, private):
    path = Path(path)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    if not _safe_directory(path, owner=True, private=private):
        raise StateError("announcement state directory could not be created")


def ensure_private_dir(path):
    path = Path(path).absolute()
    home = state_home().absolute()
    root = feature_root().absolute()
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise StateError("announcement state path escaped its feature root") from None

    components = list(_absolute_components(home))
    for component in components:
        if not component.exists():
            _mkdir_checked(component, private=False)
        else:
            _safe_directory(component, owner=component == home)
    pkg = home / "pkg"
    _mkdir_checked(pkg, private=False)
    _mkdir_checked(root, private=True)
    current = root
    for part in relative.parts:
        current /= part
        _mkdir_checked(current, private=True)
    return path


def read_json(path):
    path = Path(path).absolute()
    if not validate_read_parent(path.parent):
        return None
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise StateError("announcement evidence path is unsafe")
    if info.st_mode & 0o077:
        raise StateError("announcement evidence file is not private")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise StateError("announcement evidence is unreadable or malformed") from None
    if not isinstance(value, dict):
        raise StateError("announcement evidence is malformed")
    return value


def atomic_json(path, value):
    path = Path(path).absolute()
    ensure_private_dir(path.parent)
    try:
        existing = path.lstat()
    except FileNotFoundError:
        existing = None
    if existing is not None and (
        stat.S_ISLNK(existing.st_mode)
        or not stat.S_ISREG(existing.st_mode)
        or existing.st_uid != os.getuid()
    ):
        raise StateError("announcement evidence path is unsafe")
    temporary = path.parent / ("." + path.name + f".{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def operation_lock(path, timeout=5.0):
    path = Path(path).absolute()
    ensure_private_dir(path.parent)
    try:
        descriptor = os.open(
            path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600
        )
    except OSError:
        raise StateError("announcement operation lock path is unsafe") from None
    info = os.fstat(descriptor)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        os.close(descriptor)
        raise StateError("announcement operation lock file is unsafe")
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise StateError("timed out waiting for announcement operation lock")
                time.sleep(0.02)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
