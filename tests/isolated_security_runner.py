"""Fail-closed entrypoint for the source-only, stdlib sandbox suite."""
import errno
import os
from pathlib import Path
import resource
import socket
import sys
import unittest


def assert_denied(action):
    try:
        action()
    except OSError as error:
        if error.errno in {errno.EPERM, errno.EROFS, errno.EACCES}:
            return
        raise
    raise RuntimeError("Required sandbox control is missing")


def main():
    if sys.platform != "linux" or os.environ.get("DASH_OFFLINE_SANDBOX") != "1":
        raise SystemExit("Use the isolated Linux launcher. This entrypoint is not a host runner.")
    if Path.cwd() != Path("/scratch") or not sys.flags.isolated or not sys.dont_write_bytecode:
        raise SystemExit("Unsafe execution context")
    if Path("/source/.env").exists() or Path("/source/.venv").exists():
        raise SystemExit("Source snapshot must not contain credentials or installed dependencies")
    assert_denied(lambda: socket.socket())
    assert_denied(lambda: os.fork())
    assert_denied(lambda: Path("/source/forbidden-write").write_text("dummy"))
    assert_denied(lambda: Path("/usr/forbidden-write").write_text("dummy"))
    assert_denied(lambda: Path("/forbidden-write").write_text("dummy"))
    if Path("/proc").exists() or Path("/mnt").exists():
        raise SystemExit("Host surfaces must not be mounted")
    bounds = {resource.RLIMIT_CPU: 20, resource.RLIMIT_AS: 512 * 1024 * 1024,
              resource.RLIMIT_FSIZE: 8 * 1024 * 1024, resource.RLIMIT_NOFILE: 64,
              resource.RLIMIT_NPROC: 1, resource.RLIMIT_CORE: 0}
    for kind, bound in bounds.items():
        hard = resource.getrlimit(kind)[1]
        if hard == resource.RLIM_INFINITY or hard > bound:
            raise SystemExit("Resource bound missing")
    fs = os.statvfs("/scratch")
    if fs.f_blocks * fs.f_frsize > 32 * 1024 * 1024:
        raise SystemExit("Scratch disk bound missing")
    # The only source search path is the approved snapshot, never the working tree.
    sys.path.insert(0, "/source/tests")
    suite = unittest.defaultTestLoader.discover("/source/tests", pattern="test_security_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
