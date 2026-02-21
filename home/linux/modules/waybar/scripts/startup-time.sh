#!/bin/sh

log=$(journalctl -b 2>/dev/null \
  | grep -m1 'systemd\[1\]: Startup finished in')

if [ -z "$log" ]; then
  echo '{"text":"N/A","class":"startup_gray"}'
  exit 0
fi

# extract number after "="
time_str=$(printf '%s\n' "$log" \
  | cut -d'=' -f2 \
  | grep -oE '[0-9]+(\.[0-9]+)?')

# validate number
echo "$time_str" | grep -qE '^[0-9]+(\.[0-9]+)?$' || {
  echo '{"text":"N/A","class":"startup_gray"}'
  exit 0
}

class=$(awk -v t="$time_str" '
  BEGIN {
    if (t > 0 && t <= 12) print "startup_green";
    else if (t > 12 && t <= 13) print "startup_yellow";
    else print "startup_red";
  }
')

printf '{"text":"%ss","class":"%s"}\n' "$time_str" "$class"
