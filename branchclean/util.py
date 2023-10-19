import subprocess


def run_git(args, stdin=None) -> bytes:
    """
    Runs git with the arguments given in args. If stdin is provided, it's used
    as the stdin to the git process. Returns a raw byte string of git's
    stdout, with final newline removed.
    """

    cmd = ["git"] + args
    res = subprocess.run(cmd, check=True, capture_output=True, input=stdin)
    return res.stdout.removesuffix(b"\n")
