import subprocess


def run_git(args, stdin=None, split=False) -> bytes | list[bytes]:
    """
    Runs git with the arguments given in args. If stdin is provided, it's used
    as the stdin to the git process. By default, returns a raw byte string of
    git's stdout, with trailing space removed.  If split is true, return a
    list of lines instead.
    """

    cmd = ["git"] + args
    res = subprocess.run(cmd, check=True, capture_output=True, input=stdin)
    out = res.stdout

    if split:
        return out.splitlines()

    return out.rstrip()
