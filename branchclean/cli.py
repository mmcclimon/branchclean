import argparse

from branchclean.cleaner import Cleaner, RemoteCleaner

ap = argparse.ArgumentParser(
    prog="git-tidy",
    description="tidy them branches",
)

ap.add_argument(
    "--upstream",
    "-u",
    help="upstream remote (default: gitbox)",
    metavar="<remote>",
    default="gitbox",
)

ap.add_argument(
    "--personal",
    "-p",
    help="personal remote (default: michael)",
    metavar="<remote>",
    default="michael",
)

ap.add_argument(
    "--eternal",
    "-e",
    help="eternal branches that should not be touched (default: main, master)",
    metavar="<branch>",
    action="append",
    default=["main", "master"],
)

ap.add_argument(
    "--ignore-prefix",
    "-i",
    help="ignore branches with names matching this prefix",
    metavar="<prefix>",
    action="append",
    default=[],
)

ap.add_argument(
    "--no-fetch",
    "-n",
    help="do not do initial fetches",
    action="store_true",
)

ap.add_argument(
    "--remote",
    help="tidy personal remote, not local branches",
    action="store_true",
)

ap.add_argument("--master", help="use master, not main", action="store_true")

ap.add_argument("--really", help="do not ask, just do", action="store_true")


def run():
    """
    This is the entry point for the CLI application. It does the arg parsing
    and constructs the thing to actually run the branch cleaner.
    """
    args = ap.parse_args()

    cls = Cleaner
    if args.remote:
        cls = RemoteCleaner

    cls(
        upstream_remote=args.upstream,
        personal_remote=args.personal,
        main_name=("master" if args.master else "main"),
        eternal_branches=set(args.eternal),
        ignore_prefixes=args.ignore_prefix,
        really=args.really,
        skip_fetch=args.no_fetch,
    ).run()
