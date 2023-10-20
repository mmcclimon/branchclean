from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from branchclean import util
from branchclean.util import run_git


@dataclass
class Branch:
    sha: util.Sha
    name: str
    merge_base: util.Sha = field(init=False)
    birth: datetime = field(init=False)  # unix timestamp
    patch_id: Optional[str] = field(init=False)

    def __post_init__(self):
        # XXX get rid of hardcoded 'main' here
        self.merge_base = util.Sha(run_git("merge-base", self.sha, "main"))
        birth = run_git("show", "-s", "--format=%ct", self.merge_base)
        self.birth = datetime.fromtimestamp(int(birth))
        self.patch_id = None

    def compute_patch_id(self) -> Optional[str]:
        if self.patch_id is not None:
            return self.patch_id

        patch = run_git("diff-tree", "--patch-with-raw", self.merge_base, self.sha)
        line = run_git("patch-id", stdin=patch)
        if len(line) == 0:
            return

        patch_id, *_ = line.split()
        self.patch_id = patch_id
        return self.patch_id
