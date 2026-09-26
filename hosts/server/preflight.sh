#!/bin/sh
# Run this locally. The VPS only serves a read-only iproute2/util-linux probe;
# all validation, prompts, and settings generation happen on the workstation.
set -eu

usage() {
  printf 'usage: %s <ssh-host>\n' "$0" >&2
  exit 2
}

section() {
  printf '\n=== %s ===\n' "$1"
}

fail_analysis() {
  printf '\nAutomatic settings setup is unavailable: %s\n' "$1" >&2
  printf 'The local settings file was not changed. Review the inventory and rerun.\n' >&2
  exit 1
}

choose() {
  prompt=$1
  values=$2
  default=${3:-0}
  count=$(printf '%s\n' "$values" | wc -l | tr -d ' ')

  while :; do
    printf '\n%s\n' "$prompt" >&2
    index=0
    printf '%s\n' "$values" | while IFS='|' read -r _value label; do
      printf '  [%s] %s\n' "$index" "$label" >&2
      index=$((index + 1))
    done
    printf 'Choose [%s]: ' "$default" >&2
    IFS= read -r answer || exit 1
    answer=${answer:-$default}
    case $answer in
      ''|*[!0-9]*) printf 'Enter a number from 0 to %s.\n' "$((count - 1))" >&2 ;;
      *)
        if [ "$answer" -lt "$count" ]; then
          printf '%s\n' "$values" | awk -F '|' -v selected="$answer" 'NR == selected + 1 { print $1 }'
          return
        fi
        printf 'Enter a number from 0 to %s.\n' "$((count - 1))" >&2
        ;;
    esac
  done
}

ask() {
  prompt=$1
  default=${2-}
  printf '%s' "$prompt" >&2
  if [ -n "$default" ]; then
    printf ' [%s]' "$default" >&2
  fi
  printf ': ' >&2
  IFS= read -r answer || exit 1
  printf '%s\n' "${answer:-$default}"
}

is_ipv4() {
  printf '%s\n' "$1" | awk -F. '
    NF != 4 { exit 1 }
    { for (i = 1; i <= 4; i++) if ($i !~ /^[0-9]+$/ || $i > 255) exit 1 }
  '
}

is_ipv6_prefix() {
  printf '%s\n' "$1" | awk '
    /^[0-9A-Fa-f:]+$/ && /:/ { exit 0 }
    { exit 1 }
  '
}

is_public_key() {
  printf '%s\n' "$1" | awk '
    $1 ~ /^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)|sk-ssh-ed25519@openssh.com|sk-ecdsa-sha2-nistp256@openssh.com)$/ && $2 ~ /^[A-Za-z0-9+\/=]+$/ { exit 0 }
    { exit 1 }
  '
}

quote_nix() {
  printf '%s' "$1" | tr -d '\r\n' | sed 's/\\/\\\\/g; s/"/\\"/g'
}

[ "$#" -eq 1 ] || usage
remote_host=$1
settings_file=${SERVER_SETTINGS_FILE:-hosts/server/settings.nix}

for command in ssh jq awk sed tr wc paste mktemp; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'missing required local command: %s\n' "$command" >&2
    exit 1
  fi
done

section "Remote read-only inventory"
if ! probe=$(ssh "$remote_host" 'sh -s' <<'REMOTE_PROBE'
set -eu
for command in ip lsblk; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'missing required remote command: %s\n' "$command" >&2
    exit 1
  }
done

{
  printf '\n=== Block devices ===\n'
  lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,SERIAL
  printf '\n=== Network interfaces ===\n'
  ip -br link
  printf '\n=== IPv4 addresses and routes ===\n'
  ip -br -4 address
  ip -4 route
  ip -4 route get 1.1.1.1 || true
  printf '\n=== IPv6 addresses and routes ===\n'
  ip -br -6 address
  ip -6 route
  ip -6 route get 2606:4700:4700::1111 || true
} >&2

lsblk --json --paths --output PATH,SIZE,TYPE,RO,MODEL
ip -j -4 address show
ip -j -4 route show default
ip -j -6 address show
ip -j -6 route show default
# A rescue/Debian host normally has no AWG interface. Preserve a sixth JSON
# document so the local parser can treat that as an empty prior VPN allocation.
ip -j -6 route show dev awg0 2>/dev/null || printf '[]\n'
if [ -r /etc/os-release ]; then
  . /etc/os-release
  printf '{"id":"%s","variantId":"%s"}\n' "${ID:-}" "${VARIANT_ID:-}"
else
  printf '{"id":"","variantId":""}\n'
fi
REMOTE_PROBE
); then
  fail_analysis "the remote JSON probe failed"
fi

if ! disks=$(printf '%s\n' "$probe" | jq -rs '
  .[0].blockdevices[] | select(.type == "disk" and .ro == false) |
  "\(.path)|\(.path)  \(.size)  \(.model // "unknown model")"
'); then
  fail_analysis "could not parse the remote block-device inventory"
fi
[ -n "$disks" ] || fail_analysis "no writable whole-disk candidate was found"

if ! boot_environment=$(printf '%s\n' "$probe" | jq -rs '
  .[6] | select(type == "object") | {
    id: (.id // ""),
    variantId: (.variantId // "")
  }
'); then
  fail_analysis "could not parse the remote operating-system inventory"
fi

is_nixos_installer=$(printf '%s\n' "$boot_environment" | jq -r '.id == "nixos" and .variantId == "installer"')

if ! ipv4_candidates=$(printf '%s\n' "$probe" | jq -rs '
  def public_ipv4:
    split(".") | map(tonumber) as $octets |
    ($octets[0] != 0 and $octets[0] != 10 and $octets[0] != 127 and
     $octets[0] < 224 and
     (($octets[0] == 100 and $octets[1] >= 64 and $octets[1] <= 127) | not) and
     (($octets[0] == 169 and $octets[1] == 254) | not) and
     (($octets[0] == 172 and $octets[1] >= 16 and $octets[1] <= 31) | not) and
     (($octets[0] == 192 and $octets[1] == 168) | not));
  .[2] as $routes |
  .[1][] as $link |
  $link.addr_info[]? |
  select(.family == "inet" and .scope == "global" and (.local | public_ipv4)) |
  .local as $address |
  .prefixlen as $prefix |
  $link.ifname as $interface |
  $routes[]? |
  select(.dev == $interface and (.gateway | type == "string")) |
  "\($interface)|\($interface)  \($address)/\($prefix) via \(.gateway)"
'); then
  fail_analysis "could not parse remote IPv4 addresses and routes"
fi
[ -n "$ipv4_candidates" ] || fail_analysis "no public IPv4 address with a default gateway was found"

disk=$(choose "Target disk on $remote_host (Disko will erase it):" "$disks")
network_choice=$(choose "WAN interface and static IPv4 route:" "$ipv4_candidates")
interface=$network_choice
route=$(printf '%s\n' "$ipv4_candidates" | awk -F '|' -v selected="$interface" '$1 == selected { print $2; exit }')
address_prefix=$(printf '%s\n' "$route" | awk '{ print $2 }')
ipv4_address=${address_prefix%/*}
ipv4_prefix=${address_prefix#*/}
ipv4_gateway=$(printf '%s\n' "$route" | awk '{ print $4 }')

while :; do
  ipv4_mode=$(ask "IPv4 mode: [0] static, [1] dhcp (static is recommended)" "0")
  case $ipv4_mode in
    0) ipv4_mode=static; break ;;
    1) ipv4_mode=dhcp; break ;;
    *) printf 'Enter 0 or 1.\n' >&2 ;;
  esac
done

nameservers_default='9.9.9.9 1.1.1.1'
while :; do
  nameservers=$(ask "DNS servers, separated by spaces" "$nameservers_default")
  valid=true
  for nameserver in $nameservers; do
    is_ipv4 "$nameserver" || valid=false
  done
  [ "$valid" = true ] && [ -n "$nameservers" ] && break
  printf 'Enter one or more valid IPv4 addresses.\n' >&2
done

while :; do
  endpoint=$(ask "Public VPN endpoint" "$ipv4_address")
  is_ipv4 "$endpoint" && break
  printf 'Enter a valid IPv4 address.\n' >&2
done

while :; do
  awg_port=$(ask "AmneziaWG UDP port" "51820")
  case $awg_port in
    ''|*[!0-9]*) ;;
    *) [ "$awg_port" -ge 1 ] && [ "$awg_port" -le 65535 ] && break ;;
  esac
  printf 'Enter a port from 1 to 65535.\n' >&2
done

while :; do
  operator_key=$(ask "Administrator SSH public key")
  is_public_key "$operator_key" && break
  printf 'Enter a complete OpenSSH public key, for example: ssh-ed25519 AAAA...\n' >&2
done

domain=$(ask "NaiveProxy domain (leave empty to disable)")
acme_email=$(ask "ACME email (leave empty to disable)")
if [ -n "$domain" ] && [ -z "$acme_email" ] || [ -z "$domain" ] && [ -n "$acme_email" ]; then
  fail_analysis "domain and ACME email must be set together"
fi

ipv6=null
ipv6_summary=disabled
if ! ipv6_network_default=$(printf '%s\n' "$probe" | jq -rs '
  first(
    .[5][]? |
    select(
      (.dst | type) == "string"
      and (.dst | test("^f[cd][0-9A-Fa-f:]*::/64$"))
    ) |
    .dst | sub("::/64$"; "")
  )
'); then
  fail_analysis "could not parse the existing awg0 IPv6 network"
fi
ipv6_network_default=${ipv6_network_default:-fd42:1234:5678:1}
if ! ipv6_candidates=$(printf '%s\n' "$probe" | jq -rs '
  .[4] as $routes |
  .[3][] as $link |
  $link.addr_info[]? |
  select(.family == "inet6" and .scope == "global") |
  .local as $address |
  .prefixlen as $prefix |
  $link.ifname as $interface |
  $routes[]? |
  # IPv6 default routers commonly use a link-local gateway address.
  select(.dev == $interface and (.gateway | type == "string")) |
  "\($address)|\($address)/\($prefix) via \(.gateway)"
'); then
  fail_analysis "could not parse remote IPv6 addresses and routes"
fi
if [ -n "$ipv6_candidates" ]; then
  enable_ipv6=$(ask "Configure IPv6 VPN egress? [y/N]" "N")
  case $enable_ipv6 in
    y|Y|yes|YES)
      ipv6_choice=$(choose "Global IPv6 address and route:" "$ipv6_candidates")
      ipv6_route=$(printf '%s\n' "$ipv6_candidates" | awk -F '|' -v selected="$ipv6_choice" '$1 == selected { print $2; exit }')
      ipv6_address_prefix=$(printf '%s\n' "$ipv6_route" | awk '{ print $1 }')
      ipv6_address=${ipv6_address_prefix%/*}
      ipv6_prefix=${ipv6_address_prefix#*/}
      ipv6_gateway=$(printf '%s\n' "$ipv6_route" | awk '{ print $3 }')
      while :; do
        ipv6_network=$(ask "VPN ULA prefix (without ::/length)" "$ipv6_network_default")
        is_ipv6_prefix "$ipv6_network" && break
        printf 'Enter an IPv6 prefix, for example fd42:1234:5678:1.\n' >&2
      done
      ipv6='configured'
      ipv6_summary=nat66
      ;;
  esac
else
  printf 'IPv6 was not detected: no global IPv6 address with a usable default route was found.\n' >&2
  while :; do
    continue_without_ipv6=$(ask "Continue setup without IPv6? [y/N]")
    case $continue_without_ipv6 in
      y|Y|yes|YES) break ;;
      ''|n|N|no|NO)
        printf 'IPv6 was not detected; setup stopped and settings were not written.\n' >&2
        exit 0
        ;;
      *) printf 'Enter y to continue without IPv6, or N to stop.\n' >&2 ;;
    esac
  done
fi

section "Proposed settings"
printf 'disk: %s\ninterface: %s\nipv4: %s %s/%s via %s\nendpoint: %s:%s\n' \
  "$disk" "$interface" "$ipv4_mode" "$ipv4_address" "$ipv4_prefix" "$ipv4_gateway" "$endpoint" "$awg_port"
printf 'ipv6: %s\nproxy: %s\n' "$ipv6_summary" "${domain:-disabled}"

printf '\nWrite these settings to local %s? [y/N]: ' "$settings_file"
IFS= read -r confirm
case $confirm in
  y|Y|yes|YES) ;;
  *) printf 'Settings were not written.\n'; exit 0 ;;
esac

nameserver_lines=$(for nameserver in $nameservers; do printf '        "%s"\n' "$(quote_nix "$nameserver")"; done)
domain_nix=null
acme_email_nix=null
[ -n "$domain" ] && domain_nix="\"$(quote_nix "$domain")\""
[ -n "$acme_email" ] && acme_email_nix="\"$(quote_nix "$acme_email")\""

if [ "$ipv6" = configured ]; then
  ipv6_nix=$(cat <<EOF
    ipv6 = {
      wanAddress = "$(quote_nix "$ipv6_address")";
      wanPrefixLength = $ipv6_prefix;
      gateway = "$(quote_nix "$ipv6_gateway")";
      vpnNetwork = "$(quote_nix "$ipv6_network")";
      vpnPrefixLength = 64;
      egress = "nat66";
    };
EOF
)
else
  ipv6_nix='    ipv6 = null;'
fi

umask 077
temporary=$(mktemp "${settings_file}.XXXXXX")
trap 'rm -f "$temporary"' EXIT
cat > "$temporary" <<EOF
# VPS-specific values generated by hosts/server/preflight.sh.
let
  operatorAuthorizedKey = "$(quote_nix "$operator_key")";
in
{
  diskDevice = "$(quote_nix "$disk")";
  swapMiB = 2048;
  domain = $domain_nix;
  acmeEmail = $acme_email_nix;
  publicEndpoint = "$(quote_nix "$endpoint")";
  network = {
    ipv4 = {
      mode = "$ipv4_mode";
      interface = "$(quote_nix "$interface")";
      address = "$(quote_nix "$ipv4_address")";
      prefixLength = $ipv4_prefix;
      gateway = "$(quote_nix "$ipv4_gateway")";
      nameservers = [
$nameserver_lines
      ];
    };
$ipv6_nix
  };
  awgPort = $awg_port;
  inherit operatorAuthorizedKey;
  sftpAuthorizedKey = operatorAuthorizedKey;
}
EOF
mv "$temporary" "$settings_file"
trap - EXIT
printf 'Wrote local %s. It is intentionally a local, uncommitted change.\n' "$settings_file"

section "Bootstrap handoff"
if [ "$is_nixos_installer" = true ]; then
  printf 'Bootstrap path: NixOS installer already running.\n'
  printf 'Continue with SERVER_AI_INSTRUCTIONS.md, "NixOS Installer Completion", step 1.\n'
else
  printf 'Bootstrap path: attempt kexec first.\n'
  printf '1. Continue with SERVER_AI_INSTRUCTIONS.md, "Kexec installation", step 1:\n'
  printf '   nix run github:nix-community/nixos-anywhere -- --flake .#server --phases kexec %s\n' "$remote_host"
  printf '2. If kexec fails, no Disko phase was run. Continue with "Provider ISO installation", step 1.\n'
fi
