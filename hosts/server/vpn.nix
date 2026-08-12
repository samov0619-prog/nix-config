{
  lib,
  pkgs,
  serverSettings,
  ...
}:
let
  enabled = serverSettings.publicEndpoint != null;
  interface = "awg0";
  network = "10.66.0";
  stateDir = "/var/lib/amneziawg";
  profileDir = "/srv/vpn-download/files";
  awgAddClient = pkgs.writeShellApplication {
    name = "awg-add-client";
    runtimeInputs = with pkgs; [
      amneziawg-tools
      coreutils
      gawk
      gnugrep
      iproute2
      qrencode
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

            if [ ! -f "$config" ]; then
              echo "${interface} has not been initialized" >&2
              exit 1
            fi
            if [ -e "$profile" ]; then
              echo "profile already exists: $name" >&2
              exit 1
            fi

            last_octet=$(awk -F '[./]' '/^AllowedIPs = ${network}\\.[0-9]+\\/32$/ { print $3 }' "$config" | sort -n | tail -n1)
            last_octet=''${last_octet:-1}
            address=$((last_octet + 1))
            if [ "$address" -gt 254 ]; then
              echo "no client addresses left" >&2
              exit 1
            fi

            umask 077
            client_private=$(awg genkey)
            client_public=$(printf '%s' "$client_private" | awg pubkey)
            server_private=$(awk -F ' = ' '/^PrivateKey = / { print $2; exit }' "$config")
            server_public=$(printf '%s' "$server_private" | awg pubkey)
            jc=$(awk -F ' = ' '/^Jc = / { print $2; exit }' "$config")
            jmin=$(awk -F ' = ' '/^Jmin = / { print $2; exit }' "$config")
            jmax=$(awk -F ' = ' '/^Jmax = / { print $2; exit }' "$config")
            s1=$(awk -F ' = ' '/^S1 = / { print $2; exit }' "$config")
            s2=$(awk -F ' = ' '/^S2 = / { print $2; exit }' "$config")
            h1=$(awk -F ' = ' '/^H1 = / { print $2; exit }' "$config")
            h2=$(awk -F ' = ' '/^H2 = / { print $2; exit }' "$config")
            h3=$(awk -F ' = ' '/^H3 = / { print $2; exit }' "$config")
            h4=$(awk -F ' = ' '/^H4 = / { print $2; exit }' "$config")

            cat >> "$config" <<EOF

      [Peer]
      # $name
      PublicKey = $client_public
      AllowedIPs = ${network}.$address/32
      EOF
            awg set ${interface} peer "$client_public" allowed-ips "${network}.$address/32"

            cat > "$profile" <<EOF
      [Interface]
      Address = ${network}.$address/32
      PrivateKey = $client_private
      DNS = ${network}.1
      Jc = $jc
      Jmin = $jmin
      Jmax = $jmax
      S1 = $s1
      S2 = $s2
      H1 = $h1
      H2 = $h2
      H3 = $h3
      H4 = $h4

      [Peer]
      PublicKey = $server_public
      Endpoint = ${serverSettings.publicEndpoint}:${toString serverSettings.awgPort}
      AllowedIPs = 0.0.0.0/0
      PersistentKeepalive = 25
      EOF
            qrencode -t ANSIUTF8 < "$profile" > "$qr"
      chown root:vpn-download "$profile" "$qr"
            chmod 0640 "$profile" "$qr"
            printf 'created %s\n' "$profile"
    '';
  };
in
{
  config = lib.mkIf enabled {
    boot.kernel.sysctl."net.ipv4.ip_forward" = 1;

    networking = {
      nat = {
        enable = true;
        externalInterface = serverSettings.wanInterface;
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
      ];
      serviceConfig = {
        Type = "oneshot";
        UMask = "0077";
      };
      script = ''
                        mkdir -p ${stateDir}/clients ${profileDir}
                        chmod 0700 ${stateDir} ${stateDir}/clients
                        chmod 0750 ${profileDir}
                chown root:vpn-download ${profileDir}

                        if [ ! -f ${stateDir}/${interface}.conf ]; then
                          private_key=$(awg genkey)
                          h1=$(od -An -N4 -tu4 /dev/urandom | tr -d ' ')
                          h2=$(od -An -N4 -tu4 /dev/urandom | tr -d ' ')
                          h3=$(od -An -N4 -tu4 /dev/urandom | tr -d ' ')
                          h4=$(od -An -N4 -tu4 /dev/urandom | tr -d ' ')
                          cat > ${stateDir}/${interface}.conf <<EOF
                [Interface]
                Address = ${network}.1/24
                ListenPort = ${toString serverSettings.awgPort}
                PrivateKey = $private_key
                Jc = 5
                Jmin = 50
                Jmax = 1000
                S1 = 15
                S2 = 100
                H1 = $h1
        H2 = $h2
        H3 = $h3
        H4 = $h4
        EOF
                        fi
      '';
    };

    environment.systemPackages = [ awgAddClient ];
  };
}
