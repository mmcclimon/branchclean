import subprocess


def run_git(args, stdin=None, chomp=False, split=False) -> bytes | list[bytes]:
    """
    Runs git with the arguments given in args. If stdin is provided, it's used
    as the stdin to the git process. By default, returns a raw byte string of
    git's stdout. If chomp is true, any trailing whitespace is stripped; this
    is useful for single-line output. If split is true, return a list of lines
    instead.
    """

    cmd = ["git"] + args
    res = subprocess.run(cmd, check=True, capture_output=True, input=stdin)
    out = res.stdout

    if chomp:
        return out.rstrip()

    if split:
        return out.splitlines()

    return out
