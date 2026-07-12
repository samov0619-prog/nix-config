#!/bin/sh

log=$(journalctl -b 2>/dev/null | grep -m1 'systemd\[1\]: Startup finished in')

if [ -z "$log" ]; then
    echo '{"text":"N/A","class":"startup_gray"}'
    exit 0
fi

# итог — часть после "="; systemd за 60с переходит на "Ymin Xs" (и "Zh …")
human=$(printf '%s' "$log" | sed 's/.*= *//; s/[. ]*$//')

secs=$(printf '%s' "$human" | awk '
  {
    h=0; m=0; s=0;
    if (match($0, /[0-9]+h/))   h = substr($0, RSTART, RLENGTH-1) + 0;
    if (match($0, /[0-9]+min/)) m = substr($0, RSTART, RLENGTH-3) + 0;
    if (match($0, /[0-9.]+s/))  s = substr($0, RSTART, RLENGTH-1) + 0;
    printf "%.3f", h*3600 + m*60 + s;
  }')

# пороги green/yellow (сек) per-host: у ноута медленный HDD + Acer-POST + Wi-Fi,
# честный "зелёный" ~18с; десктоп (SSD, кабель) строгий. Выше yellow → red.
host=$(cat /proc/sys/kernel/hostname 2>/dev/null)
case "$host" in
    laptop)
        green=20
        yellow=22
        ;;
    desktop)
        green=12
        yellow=13
        ;;
    *)
        green=15
        yellow=17
        ;;
esac

class=$(awk -v t="$secs" -v g="$green" -v y="$yellow" '
  BEGIN {
    if (t > 0 && t <= g)      print "startup_green";
    else if (t > g && t <= y) print "startup_yellow";
    else                      print "startup_red";
  }')

printf '{"text":"%s","class":"%s"}\n' "$human" "$class"
