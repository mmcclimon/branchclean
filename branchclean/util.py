import subprocess

from branchclean import log


def run_git(*args, stdin=None) -> bytes:
    """
    Runs git with the arguments given in args. If stdin is provided, it's used
    as the stdin to the git process. Returns a raw byte string of git's
    stdout, with final newline removed.
    """

    cmd = ["git"] + list(args)
    res = subprocess.run(cmd, check=True, capture_output=True, input=stdin)
    return res.stdout.removesuffix(b"\n")


def fetch(remote_name: bytes, cache=True):
    if fetch.cache.get(remote_name):
        return

    log.note(b"fetching %s" % remote_name)
    run_git("fetch", remote_name)

    if cache:
        fetch.cache[remote_name] = True


fetch.cache = {}


# refname should have refs/remotes prefix or whatever
def ref_exists(refname) -> bool:
    res = subprocess.run(["git", "show-ref", "--verify", refname], capture_output=True)
    return res.returncode == 0


class Sha(bytes):
    def short(self) -> bytes:
        return self[:8]

    def __str__(self) -> str:
        return self.decode("ascii")
