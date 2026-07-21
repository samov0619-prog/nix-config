{
  nvim-config,
  pkgs,
  ...
}:
{
  home.packages = with pkgs; [
    btop
    bind
    curl
    wget
    rsync
    zip
    openssl
    iproute2
    nftables
    tcpdump
    jdk_headless
    php
    phpPackages.composer
  ];

  xdg.configFile."nvim" = {
    source = nvim-config.neovimConfig;
    recursive = true;
  };
}
