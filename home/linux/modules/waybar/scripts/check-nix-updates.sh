#!/bin/sh
# POSIX sh
# Checks nix flake updates and writes state to cache for waybar

set -e

# --- cache -------------------------------------------------------------

CACHE_DIR=${XDG_CACHE_HOME:-"$HOME/.cache"}
CACHE="$CACHE_DIR/waybar-nix-updates"

mkdir -p "$CACHE_DIR"

fail() {
  # $1 = short error code
  printf 'error:%s\n' "$1" >"$CACHE"
  exit 0
}

# --- mark loading ------------------------------------------------------

printf 'loading\n' >"$CACHE"

# --- flake sanity ------------------------------------------------------

flake_dir=${NIX_FLAKE:-}

[ -z "$flake_dir" ] && fail "no_env"
[ ! -d "$flake_dir" ] && fail "not_dir"
[ ! -f "$flake_dir/flake.lock" ] && fail "no_lock"

# --- temp dir ----------------------------------------------------------

tmp=$(mktemp -d 2>/dev/null) || fail "tmp"
trap 'rm -rf "$tmp"' EXIT INT TERM

old="$tmp/old.lock"
new="$tmp/new.lock"

cp "$flake_dir/flake.lock" "$old" 2>/dev/null || fail "copy"

# --- nix flake update --------------------------------------------------

if ! nix flake update \
  --flake "$flake_dir" \
  --output-lock-file "$new" \
  >/dev/null 2>&1
then
  fail "nix"
fi

# --- compare -----------------------------------------------------------
hash=$(sha256sum "$flake_dir/flake.lock" | awk '{print $1}')

if cmp -s "$old" "$new"; then
  printf 'clean:%s\n' "$hash" >"$CACHE"
else
  printf 'pending:%s\n' "$hash" >"$CACHE"
fi

exit 0
