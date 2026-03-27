"""
Root conftest: mirrors all test stdout to per-module output files.

Since pytest.ini sets -s (no capture), sys.stdout goes straight to the
terminal.  We install a lightweight Tee around each test so every
print() also lands in a file under tests/outputs/.

Output layout:
    tests/outputs/tools/test_web_fetch.txt
    tests/outputs/tools/test_arxiv.txt
    ...
"""
import sys
from pathlib import Path

import pytest

OUTPUT_ROOT = Path(__file__).parent / "outputs"
TESTS_ROOT  = Path(__file__).parent


# ── Tee stream ────────────────────────────────────────────────────────────────

class _Tee:
    """Proxy that writes to the real stdout AND an output file."""

    def __init__(self, real_stream, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        self._stream = real_stream
        self._file   = filepath.open("a", encoding="utf-8")

    def write(self, data: str) -> int:
        self._stream.write(data)
        return self._file.write(data)

    def flush(self):
        self._stream.flush()
        self._file.flush()

    def close(self):
        self._file.close()

    def __getattr__(self, name):          # proxy everything else (fileno, isatty, …)
        return getattr(self._stream, name)


# ── Path helpers ──────────────────────────────────────────────────────────────

def _output_path(nodeid: str) -> Path:
    """
    'tests/tools/test_web_fetch.py::test_foo'
        → tests/outputs/tools/test_web_fetch.txt
    """
    file_part = nodeid.split("::")[0]     # 'tests/tools/test_web_fetch.py'
    p = Path(file_part)
    # nodeids are relative to the project root, so they start with 'tests/'
    # strip that leading component so the output mirrors the sub-path only
    parts = p.parts
    if parts and parts[0] == TESTS_ROOT.name:
        p = Path(*parts[1:])              # 'tools/test_web_fetch.py'
    return OUTPUT_ROOT / p.with_suffix(".txt")


# ── Pytest hook ───────────────────────────────────────────────────────────────

# Track which output files have been initialised this session
_initialised: set[Path] = set()
# Cache one Tee per output file (shared across tests in same module)
_tees: dict[Path, _Tee] = {}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    out_path = _output_path(item.nodeid)

    # Truncate once per file at the start of each session
    if out_path not in _initialised:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8")
        _initialised.add(out_path)

    # Reuse the Tee for subsequent tests in the same module
    if out_path not in _tees:
        _tees[out_path] = _Tee(sys.stdout, out_path)

    tee        = _tees[out_path]
    old_stdout = sys.stdout
    sys.stdout = tee

    sys.stdout.write(f"\n{'━' * 60}\n  {item.name}\n{'━' * 60}\n")

    yield   # setup → call → teardown

    sys.stdout = old_stdout


def pytest_sessionfinish(session, exitstatus):
    """Close all output file handles cleanly at the end of the session."""
    for tee in _tees.values():
        tee.close()
