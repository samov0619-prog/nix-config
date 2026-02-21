#!/bin/sh
# POSIX sh

CACHE_DIR=${XDG_CACHE_HOME:-"$HOME/.cache"}
CACHE="$CACHE_DIR/waybar-nix-updates"

state=$(cat "$CACHE" 2>/dev/null || true)

flake_dir=${NIX_FLAKE:-}
lock="$flake_dir/flake.lock"

is_stale() {
  cached_hash=$1

  [ -z "$flake_dir" ] && return 1
  [ ! -f "$lock" ] && return 1

  current_hash=$(sha256sum "$lock" 2>/dev/null | awk '{print $1}')

  [ -z "$cached_hash" ] && return 0
  [ -z "$current_hash" ] && return 0
  [ "$cached_hash" != "$current_hash" ]
}

case "$state" in
  loading)
    printf '{"text":"","class":"loading","tooltip":"checking nix updates…"}\n'
    ;;
  pending:*)
    ts=${state#pending:}
    if is_stale "$ts"; then
      printf '{"text":"","class":"unknown","tooltip":"state outdated, click to recheck"}\n'
    else
      printf '{"text":"","class":"pending-updates","tooltip":"flake has updates"}\n'
    fi
    ;;
  clean:*)
    ts=${state#clean:}
    if is_stale "$ts"; then
      printf '{"text":"","class":"unknown","tooltip":"state outdated, click to recheck"}\n'
    else
      printf '{"text":"","class":"updated","tooltip":"flake up to date"}\n'
    fi
    ;;
  error:*)
    reason=${state#error:}
    printf '{"text":"","class":"update-error","tooltip":"error: %s"}\n' "$reason"
    ;;
  *)
    printf '{"text":"","class":"unknown","tooltip":"click to check nix updates"}\n'
    ;;
esac
