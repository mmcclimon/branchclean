from branchclean.branch import Branch
from branchclean.util import run_git


class App:
    def __init__(self):
        self.branches = []
        self.patch_ids = {}

    def run(self):
        self.find_branches()
        self.compute_main_patch_ids()

        for branch in self.branches:
            patch_id = branch.compute_patch_id()
            if patch_id is None:
                continue

            if commit := self.patch_ids.get(patch_id):
                print(f"{branch.name.decode()} merged as {commit.decode()}")

    def find_branches(self):
        branches = run_git(
            [
                "for-each-ref",
                "--format=%(objectname) %(objecttype) %(refname) %(upstream)",
                "refs/heads",
            ],
            split=True
        )

        for line in branches:
            sha, kind, name, *rest = line.split()
            if kind != b"commit":
                continue

            upstream = rest[0] if len(rest) == 1 else None

            branch = Branch(sha=sha, name=name, upstream=upstream)
            self.branches.append(branch)

    def compute_main_patch_ids(self):
        ids = {}
        print("computing patch ids...")
        # find the oldest sha for branches, compute patch ids for everything since
        oldest = min(map(lambda b: b.birth, self.branches))

        for commit in run_git(["log", "--format=%H", "--since", oldest], split=True):
            patch = run_git(["diff-tree", "--patch-with-raw", commit])
            line = run_git(["patch-id"], stdin=patch, chomp=True)
            if len(line) == 0:
                continue

            patch_id, commit = line.split()
            ids[patch_id] = commit

        self.patch_ids = ids
