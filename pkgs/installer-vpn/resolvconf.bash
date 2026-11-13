#!@bash@/bin/bash
set -euo pipefail

# Use the configured native adapter when NixOS exposes one.
if [[ -x "@nativeResolvconf@" ]]; then
    exec "@nativeResolvconf@" "$@"
fi

# Some NixOS versions expose resolvectl but omit the resolvconf alias.
# argv[0] selects the compatibility CLI; never call plain resolvectl with -a/-d.
if [[ -x "@nativeResolvectl@" && -x "@nativeSystemctl@" ]]; then
    if "@nativeSystemctl@" --quiet is-active systemd-resolved.service; then
        exec -a resolvconf "@nativeResolvectl@" "$@"
    else
        status=$?
        # Inactive or unknown unit: keep the live installer's openresolv backend.
        # Other probe errors must not silently switch DNS managers.
        case "$status" in
            3|4) ;;
            *) exit "$status" ;;
        esac
    fi
fi

# Preserve the original live-installer backend when no system adapter is present.
# Never fall back after a native failure: two DNS managers must not compete.
exec "@openresolv@/sbin/resolvconf" "$@"
