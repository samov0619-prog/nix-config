{
  lib,
  pkgs,
  serverSettings,
  ...
}:
let
  enabled = serverSettings.publicEndpoint != null;
  ipv4 = serverSettings.network.ipv4;
  ipv6 = serverSettings.network.ipv6;
  ipv6Enabled = ipv6 != null;
  interface = "awg0";
  network = "10.66.0";
  stateDir = "/var/lib/amneziawg";
  profileDir = "/srv/vpn-download/files";
  awg31ProfileSchema = pkgs.writeText "amneziawg-3.1-profile-schema" ''
    Jc = 4
    Jmin = 10
    Jmax = 50
    S1 = 32
    S2 = 32
    S3 = 32
    S4 = 32
    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    RandomTrailers = on
    DisableCookies = on
  '';
  awgAddClient = pkgs.writeShellApplication {
    name = "awg-add-client";
    runtimeInputs = with pkgs; [
      amneziawg-tools
      coreutils
      gawk
      gnugrep
      iproute2
      qrencode
      util-linux
    ];
    text = ''
            set -euo pipefail

            if [ "$#" -ne 1 ] || ! [[ "$1" =~ ^[A-Za-z0-9_-]+$ ]]; then
              echo "usage: awg-add-client <name>" >&2
              exit 2
            fi

            name="$1"
            config=${stateDir}/${interface}.conf
            profile=${profileDir}/$name.conf
            qr=${profileDir}/$name.txt

            exec 9>"${stateDir}/${interface}.lock"
            flock -x 9

            if [ ! -f "$config" ]; then
              echo "${interface} has not been initialized" >&2
              exit 1
            fi
            if [ -e "$profile" ]; then
              echo "profile already exists: $name" >&2
              exit 1
            fi

            last_octet=$(awk -v prefix="${network}." '$1 == "AllowedIPs" && $2 == "=" { split($3, ips, ","); address = ips[1]; if (index(address, prefix) == 1 && substr(address, length(address) - 2) == "/32") { split(address, octets, "[./]"); print octets[4] } }' "$config" | sort -n | tail -n1)
            last_octet=''${last_octet:-1}
            address=$((last_octet + 1))
            if [ "$address" -gt 254 ]; then
              echo "no client addresses left" >&2
              exit 1
            fi

            umask 077
            client_private=$(awg genkey)
            client_public=$(printf '%s' "$client_private" | awg pubkey)
            config_value() {
              awk -F ' = ' -v key="$1" '$1 ~ "^[[:space:]]*" key "$" { print $2; exit }' "$config"
            }

            server_private=$(config_value PrivateKey)
            server_public=$(printf '%s' "$server_private" | awg pubkey)
            jc=$(config_value Jc)
            jmin=$(config_value Jmin)
            jmax=$(config_value Jmax)
            s1=$(config_value S1)
            s2=$(config_value S2)
            s3=$(config_value S3)
            s4=$(config_value S4)
            h1=$(config_value H1)
            h2=$(config_value H2)
            h3=$(config_value H3)
            h4=$(config_value H4)
            header_protection_key=$(config_value HeaderProtectionKey)
            random_trailers=$(config_value RandomTrailers)
            disable_cookies=$(config_value DisableCookies)

            cat >> "$config" <<EOF

      [Peer]
      # $name
      PublicKey = $client_public
      AllowedIPs = ${network}.$address/32${lib.optionalString ipv6Enabled ", ${ipv6.vpnNetwork}::$address/128"}
      EOF
            awg set ${interface} peer "$client_public" allowed-ips "${network}.$address/32${lib.optionalString ipv6Enabled ",${ipv6.vpnNetwork}::$address/128"}"

            cat > "$profile" <<EOF
      [Interface]
      Address = ${network}.$address/32${lib.optionalString ipv6Enabled ", ${ipv6.vpnNetwork}::$address/128"}
      PrivateKey = $client_private
      DNS = ${network}.1
      Jc = $jc
      Jmin = $jmin
      Jmax = $jmax
      S1 = $s1
      S2 = $s2
      S3 = $s3
      S4 = $s4
      H1 = $h1
      H2 = $h2
      H3 = $h3
      H4 = $h4
      HeaderProtectionKey = $header_protection_key
      RandomTrailers = $random_trailers
      DisableCookies = $disable_cookies

      [Peer]
      PublicKey = $server_public
      Endpoint = ${serverSettings.publicEndpoint}:${toString serverSettings.awgPort}
      # Android recognizes client-owned split tunneling only with this exact
      # canonical full-tunnel route. Until VPS IPv6 egress is configured, ::/0
      # intentionally blocks IPv6 instead of allowing a privacy leak.
      AllowedIPs = 0.0.0.0/0, ::/0
      PersistentKeepalive = 25
      EOF
            qrencode -t ANSIUTF8 < "$profile" > "$qr"
      chown root:vpn-download "$profile" "$qr"
            chmod 0640 "$profile" "$qr"
            printf 'created %s\n' "$profile"
            cat "$qr"
    '';
  };
  awgRemoveClient = pkgs.writeShellApplication {
    name = "awg-remove-client";
    runtimeInputs = with pkgs; [
      amneziawg-tools
      coreutils
      gawk
      util-linux
    ];
    text = ''
      set -euo pipefail

      if [ "$#" -ne 1 ] || ! [[ "$1" =~ ^[A-Za-z0-9_-]+$ ]]; then
        echo "usage: awg-remove-client <name>" >&2
        exit 2
      fi

      name="$1"
      config=${stateDir}/${interface}.conf
      profile=${profileDir}/$name.conf
      qr=${profileDir}/$name.txt

      if [ ! -f "$config" ]; then
        echo "${interface} has not been initialized" >&2
        exit 1
      fi

      exec 9>"${stateDir}/${interface}.lock"
      flock -x 9

      peer=$(awk -v RS="" -v target="$name" '
        $0 ~ "^[[:space:]]*\\[Peer\\]" && $0 ~ ("(^|\n)[[:space:]]*#[[:space:]]*" target "([[:space:]]|$)") {
          print
          exit
        }
      ' "$config")
      if [ -z "$peer" ]; then
        echo "client not found: $name" >&2
        exit 1
      fi

      public_key=$(printf '%s\n' "$peer" | awk -F ' = ' '/^[[:space:]]*PublicKey[[:space:]]*=/ { print $2; exit }')
      if [ -z "$public_key" ]; then
        echo "client has no public key: $name" >&2
        exit 1
      fi

      temporary=$(mktemp "''${config}.XXXXXX")
      trap 'rm -f "$temporary"' EXIT
      awk -v RS="" -v ORS='\n\n' -v target="$name" '
        $0 ~ "^[[:space:]]*\\[Peer\\]" && $0 ~ ("(^|\n)[[:space:]]*#[[:space:]]*" target "([[:space:]]|$)") {
          next
        }
        { print }
      ' "$config" > "$temporary"

      awg set ${interface} peer "$public_key" remove
      mv "$temporary" "$config"
      trap - EXIT
      rm -f "$profile" "$qr"
      printf 'removed client %s\n' "$name"
    '';
  };
  awgListClients = pkgs.writeShellApplication {
    name = "awg-list-clients";
    runtimeInputs = with pkgs; [
      amneziawg-tools
      coreutils
      gawk
      util-linux
    ];
    text = ''
      set -euo pipefail

      config=${stateDir}/${interface}.conf
      if [ ! -f "$config" ]; then
        echo "${interface} has not been initialized" >&2
        exit 1
      fi
      if ! awg show ${interface} >/dev/null 2>&1; then
        echo "${interface} is not active" >&2
        exit 1
      fi

      exec 9>"${stateDir}/${interface}.lock"
      flock -s 9

      declare -A received sent
      while read -r public_key received_bytes sent_bytes; do
        received["$public_key"]=$received_bytes
        sent["$public_key"]=$sent_bytes
      done < <(awg show ${interface} transfer)

      printf '%-20s %-18s %14s %14s\n' CLIENT ADDRESS DOWNLOAD_GIB UPLOAD_GIB
      awk -v RS="" '
        {
          name = key = address = ""
          count = split($0, lines, "\n")
          for (line_number = 1; line_number <= count; line_number++) {
            line = lines[line_number]
            sub(/^[[:space:]]+/, "", line)
            if (line ~ /^#[[:space:]]*/) {
              sub(/^#[[:space:]]*/, "", line)
              name = line
            } else if (line ~ /^PublicKey[[:space:]]*=/) {
              sub(/^[^=]*=[[:space:]]*/, "", line)
              key = line
            } else if (line ~ /^AllowedIPs[[:space:]]*=/) {
              sub(/^[^=]*=[[:space:]]*/, "", line)
              split(line, addresses, ",")
              address = addresses[1]
              sub(/[[:space:]]+$/, "", address)
            }
          }
          if (name != "" && key != "") {
            print name "\t" key "\t" address
          }
        }
      ' "$config" | while IFS=$'\t' read -r name public_key address; do
        received_bytes=''${received[$public_key]:-0}
        sent_bytes=''${sent[$public_key]:-0}
        download=$(awk -v bytes="$sent_bytes" 'BEGIN { printf "%.2f", bytes / 1073741824 }')
        upload=$(awk -v bytes="$received_bytes" 'BEGIN { printf "%.2f", bytes / 1073741824 }')
        printf '%-20s %-18s %14s %14s\n' "$name" "$address" "$download" "$upload"
      done
    '';
  };
in
{
  config = lib.mkIf enabled {
    networking = {
      nat = {
        enable = true;
        enableIPv6 = ipv6Enabled && ipv6.egress == "nat66";
        externalInterface = ipv4.interface;
        internalInterfaces = [ interface ];
      };
      firewall.allowedUDPPorts = [ serverSettings.awgPort ];
      wg-quick.interfaces.${interface} = {
        type = "amneziawg";
        configFile = "${stateDir}/${interface}.conf";
      };
    };

    systemd.services.amneziawg-bootstrap = {
      description = "Initialize the AmneziaWG server profile";
      before = [ "wg-quick-${interface}.service" ];
      requiredBy = [ "wg-quick-${interface}.service" ];
      path = with pkgs; [
        amneziawg-tools
        coreutils
        openssl
        util-linux
      ];
      serviceConfig = {
        Type = "oneshot";
        UMask = "0077";
      };
      script = ''
        set -euo pipefail

        mkdir -p ${stateDir}/clients ${profileDir}
        chmod 0700 ${stateDir} ${stateDir}/clients
        chmod 0750 ${profileDir}
        chown root:vpn-download ${profileDir}

        config=${stateDir}/${interface}.conf
        exec 9>"${stateDir}/${interface}.lock"
        flock -x 9

        if [ -f "$config" ]; then
          private_key=$(awk -F ' = ' '/^[[:space:]]*PrivateKey[[:space:]]*=/ { print $2; exit }' "$config")
          header_protection_key=$(awk -F ' = ' '/^[[:space:]]*HeaderProtectionKey[[:space:]]*=/ { print $2; exit }' "$config")
        else
          private_key=""
          header_protection_key=""
        fi
        private_key=''${private_key:-$(awg genkey)}
        header_protection_key=''${header_protection_key:-$(openssl rand -base64 32 | tr -d '\n')}

        temporary=$(mktemp "''${config}.XXXXXX")
        trap 'rm -f "$temporary"' EXIT
        cat > "$temporary" <<EOF
        [Interface]
        Address = ${network}.1/24${lib.optionalString ipv6Enabled ", ${ipv6.vpnNetwork}::1/${toString ipv6.vpnPrefixLength}"}
        ListenPort = ${toString serverSettings.awgPort}
        PrivateKey = $private_key
        $(cat ${awg31ProfileSchema})
        HeaderProtectionKey = $header_protection_key
        # AWG2 legacy reference (disabled):
        # S1 = 15
        # S2 = 100
        # H1-H4 = randomized values
        EOF

        if [ -f "$config" ]; then
          awk -v RS="" '$0 ~ "^[[:space:]]*\\[Peer\\]" { print "\n" $0 }' "$config" >> "$temporary"
        fi
        mv "$temporary" "$config"
        trap - EXIT
      '';
    };

    # A profile schema update rebuilds persisted state before wg-quick restarts.
    systemd.services."wg-quick-${interface}".restartTriggers = [ awg31ProfileSchema ];

    environment.systemPackages = [
      awgAddClient
      awgRemoveClient
      awgListClients
    ];
  };
}
