#!/bin/sh
# Read-only VPS inventory. It intentionally never selects a disk or writes
# settings: provider routing and storage layout must be confirmed by an operator.
set -eu

section() {
  printf '\n=== %s ===\n' "$1"
}

for command in ip lsblk; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'missing required command: %s\n' "$command" >&2
    exit 1
  fi
done

section "Block devices"
lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,SERIAL

section "Network interfaces"
ip -br link

section "IPv4 addresses and routes"
ip -br -4 address
ip -4 route
ip -4 route get 1.1.1.1 || true

section "IPv6 addresses and routes"
ip -br -6 address
ip -6 route
ip -6 route get 2606:4700:4700::1111 || true
