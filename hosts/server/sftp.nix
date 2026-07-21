{
  lib,
  serverSettings,
  ...
}:
{
  users.users.vpn-download = {
    isNormalUser = true;
    createHome = false;
    group = "vpn-download";
    home = "/srv/vpn-download";
    shell = "/run/current-system/sw/bin/nologin";
    openssh.authorizedKeys.keys = lib.optional (
      serverSettings.sftpAuthorizedKey != null
    ) serverSettings.sftpAuthorizedKey;
  };
  users.groups.vpn-download = { };

  systemd.tmpfiles.rules = [
    "d /srv/vpn-download 0755 root root -"
    "d /srv/vpn-download/files 0750 root vpn-download -"
  ];

  services.openssh.extraConfig = ''
    Match User vpn-download
      ChrootDirectory /srv/vpn-download
      ForceCommand internal-sftp -d /files
      AllowTcpForwarding no
      AllowAgentForwarding no
      PermitTunnel no
      X11Forwarding no
      PasswordAuthentication no
  '';
}
