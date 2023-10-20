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

        self.branches = []
        self.remote_shas = []
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

        for line in branches.splitlines():
            sha, kind, refname, upstream = line.split(sep=" ")
            if kind != "commit":
                continue

            if m := re.match(r"refs/heads/(.*)", refname):
                name = m.group(1)
                if name in self.eternal_branches:
                    continue

                branch = Branch(sha=util.Sha(sha), name=name)
                self.branches.append(branch)

            remote = re.compile(
                r"refs/remotes/" + re.escape(self.personal_remote) + r"/(.*)"
            )
            if m := remote.match(refname):
                branch = Branch(sha=util.Sha(sha), name=m.group(1))
                self.remote_shas.append(branch)

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
            if patch_id is None:
                continue

            if commit := self.patch_ids.get(patch_id):
                log.merged(f"{branch.name} merged as {commit.short()}")
            else:
                log.note(f"{branch.name} is unmerged")

    def get_confirmation(self):
        pass

    def make_changes(self):
        pass
