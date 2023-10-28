import enum
import sys


class Color(enum.StrEnum):
    CLEAR = "0m"
    GREEN = "0;32m"
    CYAN = "0;96m"
    YELLOW = "0;93m"

    def __str__(self) -> str:
        return "\x1b[" + self

    def __bytes__(self) -> bytes:
        return b"\x1b[%s" % self.encode('ascii')


def _gen(prefix: str, color: Color):
    # I could use a library for this, but also...
    reset = Color.CLEAR
    pre = prefix.upper().encode('ascii')

    def fn(msg: bytes):
        sys.stdout.buffer.write(b"%s%-8s%s %s\n" % (color, pre, reset, msg))
        sys.stdout.buffer.flush()

    return fn


note = _gen("note", Color.CLEAR)
merged = _gen("merged", Color.GREEN)
update = _gen("update", Color.CYAN)
warn = _gen("warn", Color.YELLOW)
ok = _gen("ok", Color.GREEN)


def fatal(msg: bytes):
    sys.stdout.buffer.write(b"fatal: %s\n" % msg)
    sys.exit(1)
