#!/bin/sh
# Build the unmodified ROM into pokecrystal_vanilla.gbc, verified against the
# sha1 in roms.sha1. `make patch` diffs the Crystal+ build against this file.
#
# VANILLA_REF is pinned to the upstream commit this fork was taken from, NOT to
# a branch: Crystal+ is developed on master, so building "master" here would
# build the hack and diff it against itself.
set -eu
cd "$(dirname "$0")/.."

VANILLA_REF="${VANILLA_REF:-$(cat tools/vanilla_ref.txt)}"

# `make patch` calls this from a recipe that is not `+`-prefixed, so the
# jobserver fds are already closed while MAKEFLAGS still advertises them.
unset MAKEFLAGS MFLAGS MAKELEVEL

sha1() { if command -v sha1sum >/dev/null 2>&1; then sha1sum "$1"; else shasum "$1"; fi; }
jobs="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)"

tmp="$(mktemp -d)"
trap 'git worktree remove --force "$tmp" 2>/dev/null || true; rm -rf "$tmp"; git worktree prune 2>/dev/null || true' EXIT INT TERM HUP
git worktree add --detach "$tmp" "$VANILLA_REF" >/dev/null

# Only pokecrystal.gbc is needed. `make compare` would build all five ROMs plus
# the VC patch, serially, and piping it to `grep -q` would mask its exit status.
( cd "$tmp" && make -j"$jobs" crystal >/dev/null )

want="$(awk '$2 == "*pokecrystal.gbc" { print $1 }' "$tmp/roms.sha1")"
got="$(sha1 "$tmp/pokecrystal.gbc" | cut -c1-40)"
[ -n "$want" ] && [ "$want" = "$got" ] || {
	echo "vanilla build sha1 $got does not match roms.sha1 ($want)" >&2
	exit 1
}

cp "$tmp/pokecrystal.gbc" pokecrystal_vanilla.gbc
cp "$tmp/pokecrystal.sym" pokecrystal_vanilla.sym
git rev-parse "$VANILLA_REF" > pokecrystal_vanilla.rev
echo "pokecrystal_vanilla.gbc: $got (from $VANILLA_REF)"
