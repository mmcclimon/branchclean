# branchclean

This is basically my [Git::BranchCleaner](https://github.com/mmcclimon/Git-BranchCleaner) 
project, but in Python, and written differently.

It provides a binary, `git-tidy`, which will go through all your local
branches and find the ones that can be deleted. The perl version works by
checking commit messages, which worked well enough when the commit messages
you have locally also appeared as-is in main once merged.

At my current job, though, we squash-merge everything, and the final commit
message doesn't have any relation to the actual thing that winds up in the
main branch. The basic mode of operation is:

- Go through every local branch
- Compute patch id for that branch from where it forked from main
- Calculate patch ids for commits on main, for some period of time
- Check the patch ids against local branches

There's a lot of room for optimization here, but it now kinda sorta works, at
least enough to tell you what _can_ be deleted.

## using it

Ugh, Python is such a mess. Right now I'm "using"
[flit](https://flit.pypa.io/en/stable/index.html) for packaging, which really
just means that I used `flit init` to generate most of pyproject.toml. To
install, `flit install -s` will get you a symlinked version somewhere
sensible, which will Just Work for probably what you actually want.
