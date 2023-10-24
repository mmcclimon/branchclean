import itertools
from typing import Iterator

from branchclean import log, util
from branchclean.branch import Branch, TrackingBranch
from branchclean.util import run_git


class Cleaner:
    """
    Cleaner is the class that does the actual work of tidying branches.
    Construct an object and then call run() on it, and it will do the thing.
    """

    def __init__(
        self,
        upstream_remote="gitbox",
        personal_remote="michael",
        main_name="main",
        eternal_branches=None,
        ignore_prefixes=None,
    ):
        self.upstream_remote = upstream_remote
        self.personal_remote = personal_remote
        self.main_name = main_name
        self.eternal_branches = eternal_branches or {"main", "master"}
        self.ignore_prefixes = ignore_prefixes or []

        self.branches: list[Branch] = []
        self.remote_refs: dict[str, Branch] = {}  # $name -> $remoteBranch
        self.patch_ids: dict[str, util.Sha] = {}
        self.to_delete: list[Branch] = []
        self.to_update: dict[str, util.Sha] = {}
        self.to_push: list[Branch] = []

    def run(self, really=False, skip_fetch=False):
        self.assert_local_ok()
        if not skip_fetch:
            self.do_initial_fetch()
        self.read_refs()
        self.compute_main_patch_ids()
        self.process_refs()
        if self.get_confirmation(really):
            self.make_changes()

    def assert_local_ok(self):
        for line in run_git("status", "--branch", "--porcelain=v2").splitlines():
            if not line.startswith("# branch.head"):
                continue

            branch = line.split(" ")[2]
            if branch != self.main_name:
                log.fatal(f"cannot proceed from branch {branch}")

            return

    def do_initial_fetch(self):
        util.fetch(self.upstream_remote)
        util.fetch(self.personal_remote)

    def read_refs(self):
        for sha, branchname, upstream in self._read_refs("refs/heads/"):
            if self._should_ignore_branch(branchname):
                continue

            branch = Branch(
                sha=util.Sha(sha),
                name=branchname,
                upstream=upstream,
                main=self.main_name,
            )
            self.branches.append(branch)

        remote_refs = f"refs/remotes/{self.personal_remote}/"
        for sha, branchname, upstream in self._read_refs(remote_refs):
            branch = Branch(sha=sha, name=branchname, main=self.main_name)
            self.remote_refs[branchname] = branch

    def _read_refs(
        self, prefix: str
    ) -> Iterator[tuple[util.Sha, str, TrackingBranch | None]]:
        branches = run_git(
            "for-each-ref",
            "--format=%(objectname) %(objecttype) %(refname) %(upstream)",
            prefix,
        )

        for line in branches.splitlines():
            sha, kind, refname, upstream = line.split(sep=" ")
            if kind != "commit":
                continue

            tracking = None
            if upstream:
                tracking = TrackingBranch(upstream, self.personal_remote)

            yield util.Sha(sha), refname.removeprefix(prefix), tracking

    def _should_ignore_branch(self, name: str) -> bool:
        if name in self.eternal_branches:
            return True

        for prefix in self.ignore_prefixes:
            if name.startswith(prefix):
                return True

        return False

    def compute_main_patch_ids(self):
        oldest = min((b.birth for b in self._relevant_branches()))

        ymd = oldest.date().isoformat()
        since = oldest.isoformat()
        log.note(f"computing patch ids on {self.main_name} since {ymd}...")

        for commit in run_git("log", "--format=%H", "--since", since).splitlines():
            patch = run_git("diff-tree", "--patch-with-raw", commit)
            line = run_git("patch-id", stdin=patch)
            if len(line) == 0:
                continue

            patch_id, commit = line.split()
            self.patch_ids[patch_id] = util.Sha(commit)

    def _relevant_branches(self) -> Iterator[Branch]:
        return itertools.chain(self.branches, self.remote_refs.values())

    def process_refs(self):
        for branch in self.branches:
            patch_id = branch.patch_id

            if patch_id and (commit := self.patch_ids.get(patch_id)):
                log.merged(f"{branch.name} merged as {commit.short()}")
                self.to_delete.append(branch)
                continue

            remote = self.remote_refs.get(branch.name)

            if branch.upstream and not branch.upstream.is_personal:
                self._process_external(branch, branch.upstream)
            elif remote is None:
                self._process_missing(branch)
            elif remote.sha == branch.sha:
                self._process_matched(branch)
            elif remote.sha != branch.sha:
                self._process_mismatched(branch, remote)
            else:
                assert False, "unreachable"

    def _process_external(self, branch: Branch, tracking: TrackingBranch):
        util.fetch(tracking.remote)

        if not util.ref_exists(tracking.refname):
            log.update(f"{branch.name}; {tracking} is gone, will delete local")
            self.to_delete.append(branch)
            return

        upstream_sha = util.Sha(
            run_git("show", "--no-patch", "--format=%H", tracking.refname)
        )

        if upstream_sha == branch.sha:
            log.ok(f"{branch.name} matches {tracking}")
            return

        log.update(f"{branch.name}; {tracking} has changed, will update local")
        self.to_update[branch.name] = upstream_sha

    def _process_missing(self, branch):
        log.warn(f"{branch.name} is missing on remote and is not merged")

    def _process_matched(self, branch):
        log.ok(f"{branch.name} is already up to date")

    def _process_mismatched(self, branch: Branch, remote: Branch):
        local_time = run_git("show", "--no-patch", "--format=%ct", branch.sha)
        remote_time = run_git("show", "--no-patch", "--format=%ct", remote.sha)

        if local_time > remote_time:
            log.update(f"{branch.name} is newer locally; will push")
            self.to_push.append(branch)
        else:
            log.update(f"{branch.name} is newer on remote; will update local")
            self.to_update[branch.name] = remote.sha

    def get_confirmation(self, really: bool) -> bool:
        if really:
            return True

        if not self.has_changes():
            return False

        print("\nMake changes? (y/n) ", end="")
        answer = input()
        return answer.lower() == "y"

    def has_changes(self):
        return len(self.to_delete) or len(self.to_update) or len(self.to_push)

    def make_changes(self):
        if self.to_delete:
            run_git("branch", "-D", *[b.name for b in self.to_delete])

        for branch in self.to_delete:
            log.ok(f"deleted {branch.name}")

        for branch in self.to_push:
            b = branch.name
            run_git("push", "--force-with-lease", self.personal_remote, f"{b}:{b}")
            log.ok(f"pushed {b}")

        for branchname, sha in self.to_update.items():
            run_git("update-ref", f"refs/heads/{branchname}", sha)
            log.ok(f"updated {branchname}")


class RemoteCleaner(Cleaner):
    def _relevant_branches(self) -> Iterator[Branch]:
        return itertools.chain(self.remote_refs.values())

    def process_refs(self):
        for branch in self.remote_refs.values():
            if self._should_ignore_branch(branch.name):
                continue

            branchname = f"{self.personal_remote}/{branch.name}"

            patch_id = branch.patch_id

            if patch_id and (commit := self.patch_ids.get(patch_id)):
                log.merged(f"{branchname} merged as {commit.short()}")
                self.to_delete.append(branch)
                continue

            log.note(f"{branchname} is unmerged; skipping")

    def make_changes(self):
        run_git("push", "-d", self.personal_remote, *[b.name for b in self.to_delete])

        for branch in self.to_delete:
            log.ok(f"deleted {branch.name}")
