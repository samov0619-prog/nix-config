#!/usr/bin/env bash
# Called only by Waybar events or an explicit test; no battery reads or PM actions.
if [ "$#" -ne 5 ]; then
    echo "Usage: battery-notify.sh NOTIFY_SEND PW_PLAY SOUND CLOSE warning|critical|clear|full|test" >&2
    exit 64
fi
notify_send=$1
player=$2
sound=$3
close_notification=$4
timeout=0
category=device.power.low
play_sound=true
case "$5" in
    warning)
        urgency=normal
        icon=battery-low
        title='Low Battery'
        body='Battery is low. Connect the charger.'
        ;;
    critical)
        urgency=critical
        icon=battery-caution
        title='Very Low Battery'
        body='Connect the charger immediately. The system manages the critical power action.'
        ;;
    clear)
        exec "$close_notification" --app-name=Battery --category=device.power.low
        ;;
    full)
        "$close_notification" --app-name=Battery --category=device.power.low || exit "$?"
        urgency=normal
        icon=battery-full
        title='Battery Full!'
        body='Battery is charged to 100%.'
        timeout=3000
        category=device.power.full
        play_sound=false
        ;;
    test)
        urgency=normal
        icon=battery-low
        title='Battery notification test'
        body='Test popup and standard warning sound. Battery state and power policy are unchanged.'
        timeout=15000
        category=device.power.test
        ;;
    *)
        echo "Unknown battery notification: $5" >&2
        exit 64
        ;;
esac

# Play exactly one explicit sound; do not depend on the notification daemon's
# optional sound-hint support or change the user's volume/mute settings.
notify_status=0
"$notify_send" --app-name=Battery --icon="$icon" --urgency="$urgency" \
    --expire-time="$timeout" --category="$category" \
    --hint="string:x-canonical-private-synchronous:$category" \
    --hint=boolean:suppress-sound:true "$title" "$body" || notify_status=$?
if [ "$play_sound" = true ]; then
    "$player" "$sound" || exit "$?"
fi
exit "$notify_status"
