#!/usr/bin/env bash
set -uo pipefail

_is_term() {
    case "${1,,}" in
        *alacritty*|*kitty*|*foot*|*wezterm*) return 0 ;;
        *) return 1 ;;
    esac
}

sig=$(printenv HYPRLAND_INSTANCE_SIGNATURE) || exit 1
sock="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/hypr/${sig}/.socket2.sock"

prev_term=0
while true; do
    [[ -S "$sock" ]] || { sleep 1; continue; }
    socat -U - UNIX-CONNECT:"$sock" | while IFS= read -r line; do
        [[ "$line" == activewindow\>\>* ]] || continue
        class=${line#activewindow>>}; class=${class%%,*}
        if _is_term "$class"; then
            [[ $prev_term -eq 0 ]] && hyprctl switchxkblayout all 0 >/dev/null 2>&1 || true
            prev_term=1
        else
            prev_term=0
        fi
    done
    sleep 1
done
