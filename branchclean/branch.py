from dataclasses import dataclass
from typing import Optional

from branchclean.util import run_git


@dataclass(init=False)
class Branch:
    sha: bytes
    name: bytes
    upstream: Optional[bytes]
    merge_base: Optional[bytes]
    birth: bytes  # unix timestamp

    def __init__(self, sha, name, upstream):
        self.sha = sha
        self.name = name
        self.upstream = upstream

        # XXX get rid of hardcoded 'main' here
        self.merge_base = run_git(["merge-base", self.sha, "main"])
        self.birth = run_git(
            ["show", "-s", "--format=%ct", self.merge_base],
        )

    def compute_patch_id(self):
        patch = run_git(["diff-tree", "--patch-with-raw", self.merge_base, self.sha])
        line = run_git(["patch-id"], stdin=patch)
        if len(line) == 0:
            return

        patch_id, *_ = line.split()
        return patch_id
