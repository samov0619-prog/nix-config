# Edit this configuration file to define what should be installed on
# your system. Help is available in the configuration.nix(5) man page, on
# https://search.nixos.org/options and in the NixOS manual (`nixos-help`).

{
  pkgs,
  pkgsUnstable,
  ...
}:

{
  imports = [
    # Include the results of the hardware scan.
    ./hardware.nix
  ];

  # Use the GRUB 2 boot loader.
  boot.loader.grub.enable = true;
  boot.loader.grub.efiSupport = true;
  boot.loader.grub.efiInstallAsRemovable = true;
  # boot.loader.efi.efiSysMountPoint = "/boot/efi";
  # Define on which hard drive you want to install Grub.
  boot.loader.grub.device = "nodev"; # or "nodev" for efi only
  services.automatic-timezoned.enable = true;
  boot.loader.grub.useOSProber = true;

  hardware.enableRedistributableFirmware = true;

  zramSwap = {
    enable = true;
    memoryPercent = 50;          # ~3.8 ГБ RAM под сжатый своп, вместит фактически 8–12 ГБ вкладок
  };
  swapDevices = [
    { device = "/swapfile"; size = 16 * 1024; }   # страховка от OOM на тяжёлых линковках
  ];
  boot.kernel.sysctl."vm.swappiness" = 10;

  systemd.tpm2.enable = false;

  nix.gc = {
    automatic = true;
    dates = "weekly";
    options = "";
    delete_generations = "+5";
  };

  # Configure network connections interactively with nmcli or nmtui.
  networking = {
    networkmanager.enable = true;
    hostName = "desktop";
  };

  services.v2raya = {
    enable = true;
    cliPackage = pkgs.xray;
  };

  programs.amnezia-vpn = { enable = true; package = pkgsUnstable.amnezia-vpn;
  };

  nixpkgs.config.allowUnfree = true;

  powerManagement.cpuFreqGovernor = "performance";
  services.thermald.enable = true;

  services.xserver.videoDrivers = [ "modesetting" "nvidia" ];

  hardware.graphics = {
    enable = true;
    extraPackages = with pkgs; [ intel-media-driver ];
  };

  hardware.nvidia = {
    # при апгрейде на 26.05 — вернуть
    # package = config.boot.kernelPackages.nvidiaPackages.legacy_580;

    open = false;
    modesetting.enable = true;
    prime = {
      offload.enable = true;
      offload.enableOffloadCmd = true;
      intelBusId  = "PCI:0:2:0";   # подтверждено твоим hardware.nix (00:02.0)
      nvidiaBusId = "PCI:1:0:0";   # подтверждено (01:00.0)
    };
  };

  environment.sessionVariables.LIBVA_DRIVER_NAME = "iHD";

  # Enable sound.
  # services.pulseaudio.enable = true;
  # OR
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    jack.enable = true;
  };

  services.udisks2.enable = true;
  security.polkit.enable = true;

  nix.settings = {
    max-substitution-jobs = 64;
    http-connections = 256;
    experimental-features = [
      "nix-command"
      "flakes"
    ];
  };

  programs.bash = {
    enable = true;
    loginShellInit = ''
      if [ "$XDG_VTNR" = "1" ] \
         && [ -z "$DISPLAY" ] \
         && [ -z "$WAYLAND_DISPLAY" ] \
         && uwsm check may-start; then
        exec uwsm start default
      fi
    '';
  };

  environment.systemPackages = with pkgs; [ brightnessctl ];

  # Define a user account. Don't forget to set a password with ‘passwd’.
  users.users.samov = {
    isNormalUser = true;
    extraGroups = [
      "wheel"
      "adbusers"
    ]; # Enable ‘sudo’ for the user.
    initialPassword = "changeme";
  };

  services.getty.autologinUser = "samov";
  services.getty.autologinOnce = true;

  programs.hyprland = {
    enable = true;
    withUWSM = true;
  };

  programs.steam.enable = true;

  fonts = {
    enableDefaultPackages = true;
    packages = with pkgs; [
      nerd-fonts.noto
      nerd-fonts.droid-sans-mono
    ];
  };

  programs.nix-ld = {
    enable = true;
    libraries = with pkgs; [
      stdenv.cc.cc.lib # libstdc++ — нужна большинству LSP бинарей
      zlib
      openssl
      curl
      glib
    ];
  };

  # Set your time zone.
  # time.timeZone = "Europe/Amsterdam";

  # Configure network proxy if necessary
  # networking.proxy.default = "http://user:password@proxy:port/";
  # networking.proxy.noProxy = "127.0.0.1,localhost,internal.domain";

  # Select internationalisation properties.
  # i18n.defaultLocale = "en_US.UTF-8";
  # console = {
  #   font = "Lat2-Terminus16";
  #   keyMap = "us";
  #   useXkbConfig = true; # use xkb.options in tty.
  # };

  # Enable the X11 windowing system.
  # services.xserver.enable = true;

  # Configure keymap in X11
  # services.xserver.xkb.layout = "us";
  # services.xserver.xkb.options = "eurosign:e,caps:escape";

  # Enable CUPS to print documents.
  # services.printing.enable = true;

  # Enable touchpad support (enabled default in most desktopManager).
  # services.libinput.enable = true;

  # programs.firefox.enable = true;

  # List packages installed in system profile.
  # You can use https://search.nixos.org/ to find more packages (and options).
  # environment.systemPackages = with pkgs; [
  #   vim # Do not forget to add an editor to edit configuration.nix! The Nano editor is also installed by default.
  #   git
  # ];

  # Some programs need SUID wrappers, can be configured further or are
  # started in user sessions.
  # programs.mtr.enable = true;
  # programs.gnupg.agent = {
  #   enable = true;
  #   enableSSHSupport = true;
  # };

  # List services that you want to enable:

  # Enable the OpenSSH daemon.
  # services.openssh.enable = true;

  # Open ports in the firewall.
  # networking.firewall.allowedTCPPorts = [ ... ];
  # networking.firewall.allowedUDPPorts = [ ... ];
  # Or disable the firewall altogether.
  # networking.firewall.enable = false;

  # Copy the NixOS configuration file and link it from the resulting system
  # (/run/current-system/configuration.nix). This is useful in case you
  # accidentally delete configuration.nix.
  # system.copySystemConfiguration = true;

  # This option defines the first version of NixOS you have installed on this particular machine,
  # and is used to maintain compatibility with application data (e.g. databases) created on older NixOS versions.
  #
  # Most users should NEVER change this value after the initial install, for any reason,
  # even if you've upgraded your system to a new NixOS release.
  #
  # This value does NOT affect the Nixpkgs version your packages and OS are pulled from,
  # so changing it will NOT upgrade your system - see https://nixos.org/manual/nixos/stable/#sec-upgrading for how
  # to actually do that.
  #
  # This value being lower than the current NixOS release does NOT mean your system is
  # out of date, out of support, or vulnerable.
  #
  # Do NOT change this value unless you have manually inspected all the changes it would make to your configuration,
  # and migrated your data accordingly.
  #
  # For more information, see `man configuration.nix` or https://nixos.org/manual/nixos/stable/options#opt-system.stateVersion .
  system.stateVersion = "25.11"; # Did you read the comment?
}
