{
  lib,
  pkgs,
  pkgsUnstable,
  ...
}:
{
  imports = [
    ./disko.nix
  ];

  # Draft only: never inherit Acer's hardware scan or compatibility workarounds.
  assertions = [
    {
      assertion = false;
      message = "Lenovo laptop-next is not install-ready: review hardware/PRIME IDs and target disk before removing this guard.";
    }
  ];

  networking = {
    hostName = "laptop-next";
    networkmanager.enable = true;
  };
  systemd.services.NetworkManager-wait-online.enable = false;
  hardware.enableRedistributableFirmware = true;
  hardware.cpu.intel.updateMicrocode = lib.mkDefault true;

  programs.hyprland = {
    enable = true;
    withUWSM = true;
  };
  # Same initial login workflow as Acer: one autologin on tty1 per boot -> UWSM.
  services.getty = {
    autologinUser = "samov";
    autologinOnce = true;
  };
  programs.bash.loginShellInit = ''
    if [ "$XDG_VTNR" = "1" ] \
       && [ -z "$DISPLAY" ] \
       && [ -z "$WAYLAND_DISPLAY" ] \
       && uwsm check may-start; then
      exec uwsm start default
    fi
  '';

  hardware.graphics.enable = true;
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.nvidia = {
    open = true; # RTX 5060 requires open NVIDIA kernel modules, not Nouveau.
    modesetting.enable = true;
    # PRIME mode/Bus IDs and driver branch need target inventory; no Acer IDs.
  };

  services.power-profiles-daemon.enable = true;
  # No forced performance governor, TLP/auto-cpufreq, or inherited thermald.
  # PPD starts with its default balanced policy; AC/battery automation is separate.
  services.logind.settings.Login = {
    HandleLidSwitch = "ignore";
    HandleLidSwitchExternalPower = "ignore";
    HandleLidSwitchDocked = "ignore";
    HandlePowerKey = "ignore";
    HandleSuspendKey = "ignore";
    HandleHibernateKey = "ignore";
  };

  # Start without zram. Revisit only after sustained memory pressure in normal
  # workloads: low MemAvailable plus memory PSI, disruptive swap I/O or OOMs.
  # Used swap or low "free" RAM alone is not a reason; review app/Java heap first.
  # Optional starting point (~16 GiB logical capacity, not preallocated RAM):
  # zramSwap = {
  #   enable = true;
  #   memoryPercent = 50;
  #   algorithm = "zstd";
  # };
  # If enabled later, keep its priority above disk swap and repeat resume tests.
  # The separate 48 GiB disk swap remains the hibernation target, not zram.

  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    jack.enable = true;
  };
  hardware.bluetooth.enable = true;
  services.blueman.enable = true;
  services.udisks2.enable = true;
  security.polkit.enable = true;
  services.avahi = {
    enable = true;
    nssmdns4 = true;
    openFirewall = true;
  };

  services.v2raya = {
    enable = true;
    cliPackage = pkgs.xray;
  };
  programs.amnezia-vpn = {
    enable = true;
    package = pkgs.amnezia-vpn;
  };
  systemd.services.AmneziaVPN.path = lib.mkAfter [
    pkgs.iptables
    pkgs.gawk
  ];
  warnings = lib.optional (lib.versionAtLeast pkgsUnstable.amnezia-vpn.version "5.0.3.1") ''
    A newer nixpkgs-unstable AmneziaVPN (${pkgsUnstable.amnezia-vpn.version}) is available after the broken Linux 5.0.3.0 test. Before replacing the local ${pkgs.amnezia-vpn.version} override, verify upstream PR #2840 and #3231, then build and connection-test the package.
  '';

  # Deliberately public bootstrap credentials, as requested for initial setup.
  # A later manual passwd change survives activation; never put a real secret here.
  users.mutableUsers = true;
  users.users.samov = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    initialPassword = "changeme";
  };
  security.sudo.wheelNeedsPassword = true;
  # No Hyprlock/idle locking or fprintd yet; revisit authentication on live Lenovo.
  nixpkgs.config.allowUnfree = true;
  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];
  programs.steam.enable = true;
  programs.nix-ld = {
    enable = true;
    libraries = with pkgs; [
      stdenv.cc.cc.lib
      zlib
      openssl
      curl
      glib
    ];
  };
  environment.systemPackages = [ pkgs.brightnessctl ];
  fonts = {
    enableDefaultPackages = true;
    packages = with pkgs; [
      nerd-fonts.noto
      nerd-fonts.droid-sans-mono
    ];
  };

  boot.loader.grub = {
    enable = true;
    efiSupport = true;
    efiInstallAsRemovable = true;
    device = "nodev";
  };

  nix.gc = {
    # Lenovo-only: retain ten NixOS generations and collect weekly.
    automatic = true;
    dates = "weekly";
    delete_generations = "+10";
  };
  # The shared pre-GC service prunes standalone HM before the same store GC.
  samov.profileGc.homeManager.keep = 10;

  # Plain ext4 + 48 GiB swap are agreed; verify the target disk before installation.
  # Local installer use needs no IP: see ../disko/README.md.
  system.stateVersion = "26.05";
}
