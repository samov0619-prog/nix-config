{ ... }:
{
  services.adguardhome = {
    enable = true;
    host = "127.0.0.1";
    port = 8008;
    mutableSettings = true;
    settings = {
      dns = {
        bind_hosts = [
          "127.0.0.1"
          "10.66.0.1"
        ];
        port = 53;
        anonymize_client_ip = true;
        refuse_any = true;
        upstream_dns = [
          "https://dns.quad9.net/dns-query"
          "https://cloudflare-dns.com/dns-query"
        ];
        bootstrap_dns = [
          "9.9.9.10"
          "149.112.112.10"
        ];
        upstream_mode = "load_balance";
        cache_size = 4194304;
        cache_enabled = true;
        hostsfile_enabled = true;
      };
      querylog = {
        enabled = true;
        interval = "24h";
        size_memory = 1000;
      };
      statistics = {
        enabled = true;
        interval = "24h";
      };
      filtering = {
        filtering_enabled = true;
        blocking_mode = "default";
        protection_enabled = true;
        filters_update_interval = 24;
      };
      filters = [
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt";
          name = "AdGuard DNS filter";
          id = 1;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_59.txt";
          name = "AdGuard DNS Popup Hosts filter";
          id = 1777396079;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_3.txt";
          name = "Peter Lowe's Blocklist";
          id = 1777396080;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_33.txt";
          name = "Steven Black's List";
          id = 1777396081;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_39.txt";
          name = "Dandelion Sprout's Anti Push Notifications";
          id = 1777396082;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_63.txt";
          name = "HaGeZi's Windows/Office Tracker Blocklist";
          id = 1777396083;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_36.txt";
          name = "LIT: EasyList Lithuania";
          id = 1777396084;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_30.txt";
          name = "Phishing URL Blocklist (PhishTank and OpenPhish)";
          id = 1777396085;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_12.txt";
          name = "Dandelion Sprout's Anti-Malware List";
          id = 1777396086;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_8.txt";
          name = "NoCoin Filter List";
          id = 1777396087;
        }
        {
          enabled = true;
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt";
          name = "Malicious URL Blocklist (URLHaus)";
          id = 1777396088;
        }
      ];
    };
  };
}
