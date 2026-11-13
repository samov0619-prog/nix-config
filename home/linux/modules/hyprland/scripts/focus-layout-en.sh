#!/usr/bin/env bash
# Shared focus-based layout policy for terminals and Qt pinentry.
set -uo pipefail

_is_term() {
    case "${1,,}" in
        *alacritty*|*kitty*|*foot*|*wezterm*) return 0 ;;
        *) return 1 ;;
    esac
}

_is_pinentry() {
    case "${1,,}" in
        org.gnupg.pinentry-qt|pinentry-qt|pinentry) return 0 ;;
        *) return 1 ;;
    esac
}

_focus_events() {
    local prev_term=0 line class
    while IFS= read -r line; do
        [[ "$line" == activewindow\>\>* ]] || continue
        class=${line#activewindow>>}; class=${class%%,*}
        if _is_pinentry "$class"; then
            # Every pinentry focus, including another dialog of the same class.
            # Do not enforce EN on activelayout events: manual changes are allowed.
            prev_term=0
            hyprctl switchxkblayout all 0 >/dev/null 2>&1 || true
        elif _is_term "$class"; then
            [[ $prev_term -eq 0 ]] && hyprctl switchxkblayout all 0 >/dev/null 2>&1 || true
            prev_term=1
        else
            prev_term=0
        fi
    done
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    sig=$(printenv HYPRLAND_INSTANCE_SIGNATURE) || exit 1
    sock="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/hypr/${sig}/.socket2.sock"

    while true; do
        [[ -S "$sock" ]] || { sleep 1; continue; }
        socat -U - UNIX-CONNECT:"$sock" | _focus_events
        sleep 1
    done
fi
