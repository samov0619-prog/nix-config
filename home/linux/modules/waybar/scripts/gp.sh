#!/bin/sh

# POSIX sh, no zsh/bash extensions

# get gpu utilization (%) and used memory (MB)
gpu_data=$(nvidia-smi \
  --query-gpu=utilization.gpu,memory.used \
  --format=csv,noheader,nounits 2>/dev/null) || exit 1

# expected: "12, 345"
gpu_util=$(printf '%s\n' "$gpu_data" | cut -d',' -f1 | tr -d ' ')
mem_mb=$(printf '%s\n' "$gpu_data" | cut -d',' -f2 | tr -d ' ')

# convert MB -> GB (1 decimal)
mem_gb=$(awk "BEGIN { printf \"%.1f\", $mem_mb / 1024 }")

printf 'gpu:%s%%|%sGB ' "$gpu_util" "$mem_gb"
