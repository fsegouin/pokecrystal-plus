#!/bin/sh
set -e

# The build must not modify any tracked file: every generated file belongs in
# .gitignore. This inspects tracked paths only, so untracked output is not
# detected here.
#
# The refresh clears stale stat entries, so a file the build touched without
# changing does not trip --quiet, which bails on the first stat mismatch
# without comparing contents.
git update-index -q --refresh
if ! git diff-index --quiet HEAD --; then
    echo 'Modified tracked files detected:'
    git diff-index HEAD --
    exit 1
fi
