import subprocess

from branchclean import log


def run_git(*args, stdin=None, raw=False) -> str | bytes:
    """
    Runs git with the arguments given in args. If stdin is provided, it's used
    as the stdin to the git process. If raw is true, returns a raw byte string
    of git's stdout (including the trailing newline). If raw is not true,
    assumes that the output is utf-8, and returns string with final newline
    removed.
    """

    cmd = ["git"] + list(args)
    kwargs = {
            "check": True,
            "capture_output": True,
            "input": stdin
            }

    if not raw:
        kwargs["encoding"] = "utf8"

    res = subprocess.run(cmd, **kwargs)

    if raw:
        return res.stdout

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
