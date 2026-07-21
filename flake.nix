# ── stateVersion policy ───────────────────────────────────────────────
# stateVersion is per-host. Existing desktop/laptop/mac retain 25.11 via
# the mkDefault in home/users/samov/default.nix. Fresh server imports
# home/users/samov/state-26.05.nix and declares system.stateVersion = "26.05".
#
# For another fresh host, add its system stateVersion and explicitly import
# state-26.05.nix in that host's Home Manager module list below. This keeps host
# composition visible in flake.nix without changing legacy hosts.
#
# Once every host has moved to 26.05, delete state-26.05.nix and change the
# common mkDefault in home/users/samov/default.nix to "26.05". Then remove any
# no-longer-needed compatibility branches gated by home.stateVersion.
# ─────────────────────────────────────────────────────────────────────
{
  description = "NixOS & stanadalone home-manager flake";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-26.05";
    nixpkgs-unstable.url = "nixpkgs/nixpkgs-unstable";

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nvim-config.url = "github:samov0619-prog/nvim";
    xremap-flake = {
      url = "github:xremap/nix-flake";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    freesm = {
      url = "github:FreesmTeam/FreesmLauncher";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nix-gc-env.url = "github:Julow/nix-gc-env";
  };

  outputs =
    {
      self,
      nixpkgs,
      nixpkgs-unstable,
      home-manager,
      nvim-config,
      freesm,
      nix-gc-env,
      xremap-flake,
      ...
    }:
    let
      lib = nixpkgs.lib;

      systems = {
        linux = "x86_64-linux";
        mac = "aarch64-darwin";
      };

      pkgsFor =
        system: overlays:
        import nixpkgs {
          inherit system overlays;
        };

      pkgsUnstableFor =
        system:
        import nixpkgs-unstable {
          inherit system;
        };

      mkHM =
        {
          pkgs,
          username,
          modules,
        }:
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs modules;
          extraSpecialArgs = {
            inherit username nvim-config xremap-flake;
            pkgsUnstable = pkgsUnstableFor pkgs.stdenv.hostPlatform.system;
          };
        };

      mkNixos =
        {
          system,
          modules,
        }:
        lib.nixosSystem {
          inherit system;
          specialArgs = {
            pkgsUnstable = pkgsUnstableFor system;
          };
          modules = modules ++ [
            home-manager.nixosModules.home-manager
            nix-gc-env.nixosModules.default
          ];
        };
    in
    {
      overlays = {
        filemanager1-common = final: prev: {
          filemanager1-common = final.callPackage ./pkgs/filemanager1-common { };
        };
      };

      nixosConfigurations = {
        desktop = mkNixos {
          system = systems.linux;
          modules = [
            ./hosts/desktop
          ];
        };

        laptop = mkNixos {
          system = systems.linux;
          modules = [
            ./hosts/laptop
          ];
        };

        server = mkNixos {
          system = systems.linux;
          modules = [
            ./hosts/server
          ];
        };
      };

      homeConfigurations = {
        samov-desktop = mkHM {
          pkgs = pkgsFor systems.linux [
            self.overlays.filemanager1-common
            freesm.overlays.default
          ];
          username = "samov";
          modules = [
            ./home/users/samov

            ./home/core-set
            ./home/gui-set
            ./home/modules/minecraft/server
            ./home/apps/minecraft
            ./home/apps/creative.nix

            ./home/linux/desktop
          ];
        };

        samov-laptop = mkHM {
          pkgs = pkgsFor systems.linux [
            self.overlays.filemanager1-common
            freesm.overlays.default
          ];
          username = "samov";
          modules = [
            ./home/users/samov

            ./home/core-set
            ./home/gui-set
            ./home/modules/minecraft/server
            ./home/apps/minecraft
            ./home/apps/creative.nix

            ./home/linux/laptop
          ];
        };

        samov-server = mkHM {
          pkgs = pkgsFor systems.linux [ ];
          username = "samov";
          modules = [
            ./home/users/samov
            ./home/users/samov/state-26.05.nix

            ./home/core-set
            ./home/modules/minecraft/server
            ./home/linux/server
          ];
        };

        samov-mac = mkHM {
          pkgs = pkgsFor systems.mac [ ];
          username = "samov";
          modules = [
            ./home/users/samov
            ./home/core-set
          ];
        };
      };
    };
}
