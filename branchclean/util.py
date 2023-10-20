import subprocess

from branchclean import log


def run_git(*args, stdin=None) -> str:
    """
    Runs git with the arguments given in args. If stdin is provided, it's used
    as the stdin to the git process. Returns a raw byte string of git's
    stdout, with final newline removed.
    """

    cmd = ["git"] + list(args)
    res = subprocess.run(
        cmd, check=True, capture_output=True, encoding="utf8", input=stdin
    )
    return res.stdout.removesuffix("\n")


def fetch(remote_name: str, cache=True):
    if fetch.cache.get(remote_name):
        return

    log.note(f"fetching {remote_name}")
    run_git("fetch", remote_name)

    if cache:
        fetch.cache[remote_name] = True


fetch.cache = {}


# refname should have refs/remotes prefix or whatever
def ref_exists(refname) -> bool:
    res = subprocess.run(["git", "show-ref", "--verify", refname], capture_output=True)
    return res.returncode == 0


class Sha(str):
    def short(self) -> str:
        return self[:8]
