import enum
import sys


class Color(enum.StrEnum):
    CLEAR = "0m"
    GREEN = "0;32m"
    CYAN = "0;96m"
    YELLOW = "0;93m"

    def __str__(self) -> str:
        return "\x1b[" + self


def _gen(prefix: str, color: Color):
    # I could use a library for this, but also...
    reset = Color.CLEAR

    def fn(msg: str):
        print(f"{color}{prefix.upper():8}{reset} {msg}")

    return fn


note = _gen("note", Color.CLEAR)
merged = _gen("merged", Color.GREEN)
update = _gen("update", Color.CYAN)
warn = _gen("warn", Color.YELLOW)
ok = _gen("ok", Color.GREEN)


def fatal(msg: str):
    print("fatal: " + msg)
    sys.exit(1)
