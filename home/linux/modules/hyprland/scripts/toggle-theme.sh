#!/bin/sh
set -eu

# POSIX-compliant theme toggler
readonly THEME_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/theme/current_theme"

readonly ALACRITTY_THEME="${XDG_CONFIG_HOME:-$HOME/.config}/alacritty/current-theme.toml"
readonly ALACRITTY_THEMES_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/alacritty/themes"

# Get current theme from gsettings
current=$(dconf read /org/gnome/desktop/interface/color-scheme 2>/dev/null || true)
# Remove quotes - POSIX way
current=$(printf '%s' "$current" | tr -d "'")

# Determine next theme
case "$current" in
    prefer-dark)
        next='prefer-light'
        theme='light'
        gtk_theme='Adwaita'
        ;;
    prefer-light)
        next='prefer-dark'
        theme='dark'
        gtk_theme='Adwaita-dark'
        ;;
    *)
        # Default to dark if unset/unknown
        next='prefer-dark'
        theme='dark'
        gtk_theme='Adwaita-dark'
        ;;
esac

# Apply GNOME theme
dconf write /org/gnome/desktop/interface/color-scheme "'$next'"
# GTK3 (including Blueman) follows gtk-theme, not just the newer color-scheme.
# Its native Wayland settings/portal notifications update already open windows.
dconf write /org/gnome/desktop/interface/gtk-theme "'$gtk_theme'"

# Native qtct directory watchers update already running Qt applications.
qt-theme-apply --mode "$theme"

# Переключаем тему Alacritty через симлинк
if [ -d "$ALACRITTY_THEMES_DIR" ]; then
    rm -f "$ALACRITTY_THEME"
    ln -sf "${ALACRITTY_THEMES_DIR}/${theme}.toml" "$ALACRITTY_THEME"
    
    # Перезагружаем конфиг во всех запущенных экземплярах Alacritty
    # Это работает только если в конфиге включен live config reload (по умолчанию включен)
    # touch "$ALACRITTY_THEME"
fi

# Ardour reads the desktop mode through its launcher on the next startup.
# Never edit ui_config while the application may be using/saving it.

# Hyprland notification (if hyprctl available)
if command -v hyprctl >/dev/null 2>&1; then
    hyprctl notify 5 3000 'rgb(ff1ea3)' "🌗 ${theme}" || true
fi

# Save current theme
mkdir -p "$(dirname "$THEME_FILE")"
printf '%s' "$theme" > "$THEME_FILE"
