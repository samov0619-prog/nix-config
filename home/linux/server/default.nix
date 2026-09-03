{ pkgs, ... }:
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
    gnutar
  ];
}
