from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from branchclean import util
from branchclean.util import run_git


@dataclass
class Branch:
    sha: util.Sha
    name: str
    upstream: Optional[str]
    merge_base: util.Sha = field(init=False)
    birth: datetime = field(init=False)  # unix timestamp

    def __post_init__(self):
        # XXX get rid of hardcoded 'main' here
        self.merge_base = util.Sha(run_git("merge-base", self.sha, "main"))
        birth = run_git("show", "-s", "--format=%ct", self.merge_base)
        self.birth = datetime.fromtimestamp(int(birth))

    def compute_patch_id(self):
        patch = run_git("diff-tree", "--patch-with-raw", self.merge_base, self.sha)
        line = run_git("patch-id", stdin=patch)
        if len(line) == 0:
            return

        patch_id, *_ = line.split()
        return patch_id
