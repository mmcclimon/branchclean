import re

from branchclean import log, util
from branchclean.branch import Branch
from branchclean.util import run_git


class Cleaner:
    def __init__(self):
        # TODO: config
        self.upstream_remote = "gitbox"
        self.personal_remote = "michael"
        self.eternal_branches = {"main", "master"}
        self.ignore_prefixes = ["boneyard/"]

        self.branches = []
        self.remote_shas = []
        self.other_upstreams = {}
        self.patch_ids = {}

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
            if branch != "main":
                log.fatal(f"cannot proceed from branch {branch}")

            return

    def do_initial_fetch(self):
        util.fetch(self.upstream_remote)
        util.fetch(self.personal_remote)

    def read_refs(self):
        branches = run_git(
            "for-each-ref",
            "--format=%(objectname) %(objecttype) %(refname) %(upstream)",
            "refs/heads",
            f"refs/remotes/{self.personal_remote}",
        )

        personal_re = re.escape(self.personal_remote)

        for line in branches.splitlines():
            sha, kind, refname, upstream = line.split(sep=" ")
            if kind != "commit":
                continue

            if m := re.match(r"refs/heads/(.*)", refname):
                name = m.group(1)
                if self._should_ignore_branch(name):
                    continue

                if upstream and not re.match(f"refs/remotes/{personal_re}/", upstream):
                    self.other_upstreams[name] = upstream.removeprefix("refs/remotes/")

                branch = Branch(sha=util.Sha(sha), name=name)
                self.branches.append(branch)

            if m := re.match(rf"refs/remotes/{personal_re}/(.*)", refname):
                branch = Branch(sha=util.Sha(sha), name=m.group(1))
                self.remote_shas.append(branch)

    def _should_ignore_branch(self, name: str) -> bool:
        if name in self.eternal_branches:
            return True

        for prefix in self.ignore_prefixes:
            if name.startswith(prefix):
                return True

        return False

    def compute_main_patch_ids(self):
        # find the oldest sha for branches, compute patch ids for everything since
        oldest = min(map(lambda b: b.birth, self.branches + self.remote_shas))

        ymd = oldest.date().isoformat()
        since = oldest.isoformat()
        log.note(f"computing patch ids since {ymd}...")

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

            if commit := self.patch_ids.get(patch_id):
                log.merged(f"{branch.name} merged as {commit.short()}")
                continue

            # This is goofy: store these in a better way.
            remotes = list(filter(lambda r: r.name == branch.name, self.remote_shas))
            remote = remotes[0] if len(remotes) else None

            if tracking := self.other_upstreams.get(branch.name):
                self._process_external(branch, tracking)
            elif remote is None:
                self._process_missing(branch)
            elif remote.sha == branch.sha:
                self._process_matched(branch)
            elif remote.sha != branch.sha:
                self._process_mismatched(branch, remote)
            else:
                assert False, "unreachable"

    def _process_external(self, branch: Branch, tracking: str):
        remote, _ = tracking.split("/", maxsplit=2)
        util.fetch(remote)

        if not util.ref_exists("refs/remotes/" + tracking):
            log.update(f"{branch.name}; {tracking} is gone, will delete local")
            return

        upstream_sha = run_git(
            "show", "--no-patch", "--format=%H", "refs/remotes/" + tracking
        )

        if upstream_sha == branch.sha:
            log.ok(f"{branch.name} matches {tracking}")
            return

        log.update(f"{branch.name}; {tracking} has changed, will update local")

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
        else:
            log.update(f"{branch.name} is newer on remote; will update local")

    def get_confirmation(self):
        pass

    def make_changes(self):
        pass
