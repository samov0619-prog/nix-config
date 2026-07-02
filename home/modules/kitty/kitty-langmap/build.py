#!/usr/bin/env python3
# Build-time вариант langmap: config + map.txt -> stdout.
# Логика идентична kitty-langmap/main.py, но без бэкапа и правки на месте —
# чистая функция для использования в деривации Nix.
import sys

config_path, map_path = sys.argv[1], sys.argv[2]

with open(map_path) as f:
    m = f.readlines()
map_dict = dict(zip(m[0].strip(), m[1].strip()))

with open(config_path) as f:
    lines = f.readlines()

out = []
for line in lines:
    if ' map ' not in line or line.startswith('#::'):
        out.append(line)
        continue
    parts = line.split(' ')
    ki = parts.index('map') + 1
    parts_keys = parts[ki].split('+')
    new_keys = '+'.join(map_dict.get(k, k) for k in parts_keys)
    new_line = ''
    for i, part in enumerate(parts):
        new_line += (new_keys if i == ki else part) + ' '
    if line.startswith('#'):
        line = line[1:].strip() + '\n'
        new_line = new_line[1:].strip() + '\n'
    out.append(line)
    out.append(new_line)

sys.stdout.write(''.join(out))
