from datetime import datetime
from dataclasses import dataclass, field, InitVar
from typing import Optional
import functools
import re

from branchclean import util
from branchclean.util import run_git


class TrackingBranch:
    def __init__(self, refname: str, personal_remote: str):
        m = re.match(r"refs/remotes/(.*?)/(.*)", refname)
        if not m:
            raise ValueError(f"invalid refname: {refname}")

        self.remote = m.group(1)
        self.name = m.group(2)
        self.is_personal = self.remote == personal_remote

    @property
    def refname(self) -> str:
        return f"refs/remotes/{self.remote}/{self.name}"

    def __str__(self) -> str:
        return f"{self.remote}/{self.name}"


@dataclass
class Branch:
    sha: util.Sha
    name: str
    upstream: Optional[TrackingBranch] = None
    merge_base: util.Sha = field(init=False)
    birth: datetime = field(init=False)  # unix timestamp
    main: InitVar[str] = "main"

    def __post_init__(self, main):
        self.merge_base = util.Sha(run_git("merge-base", self.sha, main))
        birth = run_git("show", "-s", "--format=%ct", self.merge_base)
        self.birth = datetime.fromtimestamp(int(birth))

    @functools.cached_property
    def patch_id(self) -> Optional[str]:
        patch = run_git("diff-tree", "--patch-with-raw", self.merge_base, self.sha)
        line = run_git("patch-id", stdin=patch)
        if len(line) == 0:
            return

        patch_id, *_ = line.split()
        return patch_id
