from typing import Iterator

from branchclean import log, util
from branchclean.branch import Branch, TrackingBranch
from branchclean.util import run_git


class Cleaner:
    def __init__(self):
        # TODO: config
        self.upstream_remote = "gitbox"
        self.personal_remote = "michael"
        self.eternal_branches = {"main", "master"}
        self.ignore_prefixes = ["boneyard/"]
        self.main_name = "main"
        self.really = False

        self.branches: list[Branch] = []
        self.remote_shas: dict[str, Branch] = {}  # $name -> $remoteBranch
        self.patch_ids: dict[str, util.Sha] = {}
        self.to_delete: list[Branch] = []
        self.to_update: dict[str, util.Sha] = {}
        self.to_push: list[Branch] = []

    def run(self):
        self.assert_local_ok()
        self.do_initial_fetch()
        self.read_refs()
        self.compute_main_patch_ids()
        self.process_refs()
        self.get_confirmation()
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

            branch = Branch(sha=util.Sha(sha), name=branchname, upstream=upstream)
            self.branches.append(branch)

        remote_refs = f"refs/remotes/{self.personal_remote}/"
        for sha, branchname, upstream in self._read_refs(remote_refs):
            branch = Branch(sha=sha, name=branchname)
            self.remote_shas[branchname] = branch

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
        # find the oldest sha for branches, compute patch ids for everything since
        oldest = min(
            [b.birth for b in self.branches]
            + [b.birth for b in self.remote_shas.values()]
        )

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

    def process_refs(self):
        for branch in self.branches:
            patch_id = branch.compute_patch_id()

            if patch_id and (commit := self.patch_ids.get(patch_id)):
                log.merged(f"{branch.name} merged as {commit.short()}")
                self.to_delete.append(branch)
                continue

            remote = self.remote_shas.get(branch.name)

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

        # TODO: actually do things here
        if local_time > remote_time:
            log.update(f"{branch.name} is newer locally; will push")
            self.to_push.append(branch)
        else:
            log.update(f"{branch.name} is newer on remote; will update local")
            self.to_update[branch.name] = remote.sha

    def get_confirmation(self):
        if not self.has_changes():
            return

        print("\nMake changes? (y/n) ", end="")
        answer = input()
        if answer.lower() == "y":
            self.really = True

    def has_changes(self):
        return len(self.to_delete) or len(self.to_update) or len(self.to_push)

    def make_changes(self):
        if not self.really:
            return

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
