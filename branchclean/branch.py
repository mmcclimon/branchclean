from dataclasses import dataclass, field
from typing import Optional

from branchclean import util
from branchclean.util import run_git


@dataclass
class Branch:
    sha: util.Sha
    name: bytes
    upstream: Optional[bytes]
    merge_base: util.Sha = field(init=False)
    birth: bytes = field(init=False)  # unix timestamp

    def __post_init__(self):
        # XXX get rid of hardcoded 'main' here
        self.merge_base = util.Sha(run_git(["merge-base", self.sha, "main"]))
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
