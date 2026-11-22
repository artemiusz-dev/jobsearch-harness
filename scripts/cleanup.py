#!/usr/bin/env python3
"""
Workspace cleanup. Removes temp files: LibreOffice lock files, .DS_Store, *.tmp, unpacked docx dirs.
Dry-run by default; never touches the backup dir, node_modules or .git.

Usage:
    python3 scripts/cleanup.py [--workspace DIR]              # dry-run
    python3 scripts/cleanup.py [--workspace DIR] --execute    # actually delete
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jobprofile import ProfileError, add_workspace_arg, load_profile  # noqa: E402

FILE_NAMES = {".DS_Store"}
FILE_SUFFIXES = (".tmp",)
FILE_PREFIXES = (".~lock.",)       # LibreOffice stale lock files
DIR_NAMES = {"unpacked"}           # temp docx unpacked dirs
SKIP_DIRS = {"node_modules", ".git", ".venv", "__pycache__"}


def find_targets(workspace: Path, backup_dir: str):
    files, dirs = [], []
    for root, dirnames, filenames in os.walk(workspace):
        root_path = Path(root)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and d != backup_dir]
        for fname in filenames:
            if fname in FILE_NAMES or fname.endswith(FILE_SUFFIXES) or fname.startswith(FILE_PREFIXES):
                files.append(root_path / fname)
        for dname in list(dirnames):
            if dname in DIR_NAMES:
                dirs.append(root_path / dname)
                dirnames.remove(dname)  # don't descend
    return sorted(set(files)), sorted(set(dirs))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--execute", action="store_true", help="Actually delete (default is dry-run)")
    add_workspace_arg(parser)
    args = parser.parse_args()
    try:
        prof = load_profile(args.workspace)
    except ProfileError as e:
        sys.exit(str(e))
    workspace = prof.workspace
    files, dirs = find_targets(workspace, os.path.basename(prof["paths"]["backup_dir"]))

    if not files and not dirs:
        print("Workspace is clean. Nothing to delete.")
        return
    print(f"{'EXECUTING' if args.execute else 'DRY RUN'}: found {len(files)} files and {len(dirs)} directories to remove.\n")
    skipped = 0
    for f in files:
        rel = f.relative_to(workspace)
        if args.execute:
            try:
                f.unlink()
                print(f"  DELETED  {rel}")
            except PermissionError:
                print(f"  SKIPPED  {rel}  (permission denied)")
                skipped += 1
        else:
            print(f"  [file]   {rel}")
    for d in dirs:
        rel = d.relative_to(workspace)
        if args.execute:
            try:
                shutil.rmtree(d)
                print(f"  REMOVED  {rel}/")
            except PermissionError:
                print(f"  SKIPPED  {rel}/  (permission denied)")
                skipped += 1
        else:
            print(f"  [dir]    {rel}/")
    if args.execute:
        print(f"\nDone. {skipped} item(s) skipped due to permissions." if skipped else "\nDone.")
    else:
        print("\nRun with --execute to delete.")


if __name__ == "__main__":
    main()
