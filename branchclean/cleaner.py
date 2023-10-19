from branchclean import util
from branchclean.branch import Branch
from branchclean.util import run_git


class Cleaner:
    def __init__(self):
        self.branches = []
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
        pass

    def do_initial_fetch(self):
        pass

    def read_refs(self):
        branches = run_git(
            [
                "for-each-ref",
                "--format=%(objectname) %(objecttype) %(refname) %(upstream)",
                "refs/heads",
            ],
        )

        for line in branches.splitlines():
            sha, kind, name, upstream = line.split(sep=b" ")
            if kind != b"commit":
                continue

            branch = Branch(sha=util.Sha(sha), name=name, upstream=upstream)
            self.branches.append(branch)

    def compute_main_patch_ids(self):
        print("computing patch ids...")
        # find the oldest sha for branches, compute patch ids for everything since
        oldest = min(map(lambda b: b.birth, self.branches))

        for commit in run_git(["log", "--format=%H", "--since", oldest]).splitlines():
            patch = run_git(["diff-tree", "--patch-with-raw", commit])
            line = run_git(["patch-id"], stdin=patch)
            if len(line) == 0:
                continue

            patch_id, commit = line.split()
            self.patch_ids[patch_id] = commit

    def process_refs(self):
        for branch in self.branches:
            patch_id = branch.compute_patch_id()
            if patch_id is None:
                continue

            if commit := self.patch_ids.get(patch_id):
                print(f"{branch.name.decode()} merged as {commit.decode()}")

    def get_confirmation(self):
        pass

    def make_changes(self):
        pass
