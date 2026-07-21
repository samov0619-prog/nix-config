{
  lib,
  pkgs,
  serverSettings,
  ...
}:
let
  enabled = serverSettings.domain != null && serverSettings.acmeEmail != null;
  caddyWithNaive = pkgs.caddy.withPlugins {
    plugins = [ "github.com/caddyserver/forwardproxy@v0.0.0-20260321230143-0aab84dad4fc" ];
    hash = "sha256-OBiUNnT3eDNdJKJOqO/eTwef4xTvovHX/QT6gK2NqEg=";
  };
  caddyfile = pkgs.writeText "Caddyfile" ''
    {
      email ${serverSettings.acmeEmail}
      order forward_proxy before file_server
    }

    :443, ${serverSettings.domain} {
      forward_proxy {
        hide_ip
        hide_via
        import /var/lib/naiveproxy/users.caddy
      }

      respond "Not found" 404
    }
  '';
  naiveAddClient = pkgs.writeShellApplication {
    name = "naive-add-client";
    runtimeInputs = [
      pkgs.coreutils
      pkgs.openssl
      pkgs.systemd
    ];
    text = ''
            set -euo pipefail

            if [ "$#" -ne 1 ] || ! [[ "$1" =~ ^[A-Za-z0-9_-]+$ ]]; then
              echo "usage: naive-add-client <name>" >&2
              exit 2
            fi

            name="$1"
            state_dir=/var/lib/naiveproxy
            profile=/srv/vpn-download/files/$name-naive.json
            users="$state_dir/users.caddy"

            if [ -e "$profile" ]; then
              echo "profile already exists: $name" >&2
              exit 1
      fi

      password=$(openssl rand -base64 24 | tr -d '=+/\n' | cut -c1-24)
      printf 'basic_auth %s %s\n' "$name" "$password" >> "$users"
            systemctl reload caddy

            cat > "$profile" <<EOF
      {
        "outbounds": [
          {
            "type": "naive",
            "tag": "naive-$name",
            "server": "${serverSettings.domain}",
            "server_port": 443,
            "username": "$name",
            "password": "$password",
            "tls": {
              "server_name": "${serverSettings.domain}"
            }
          }
        ]
      }
      EOF
      chown root:vpn-download "$profile"
            chmod 0640 "$profile"
            printf 'created %s\n' "$profile"
    '';
  };
in
{
  config = lib.mkIf enabled {
    networking.firewall.allowedTCPPorts = [
      80
      443
    ];

    security.acme = {
      acceptTerms = true;
      defaults.email = serverSettings.acmeEmail;
    };

    systemd.tmpfiles.rules = [
      "d /var/lib/naiveproxy 0750 root caddy -"
    ];

    systemd.services.naiveproxy-initialize = {
      description = "Initialize NaiveProxy credentials store";
      before = [ "caddy.service" ];
      requiredBy = [ "caddy.service" ];
      path = [ pkgs.openssl ];
      serviceConfig.Type = "oneshot";
      script = ''
        install -d -m 0750 -o root -g caddy /var/lib/naiveproxy
        if [ ! -e /var/lib/naiveproxy/users.caddy ]; then
          # This account has a random password that is never published, so the
          # proxy is closed until naive-add-client creates a real profile.
          printf 'basic_auth disabled %s\n' "$(openssl rand -hex 32)" > /var/lib/naiveproxy/users.caddy
          chown root:caddy /var/lib/naiveproxy/users.caddy
          chmod 0640 /var/lib/naiveproxy/users.caddy
        fi
      '';
    };

    services.caddy = {
      enable = true;
      package = caddyWithNaive;
      configFile = caddyfile;
    };

    environment.systemPackages = [ naiveAddClient ];
  };
}
