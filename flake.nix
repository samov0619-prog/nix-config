{
  description = "NixOS & stanadalone home-manager flake";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-25.11";
    nixpkgs-unstable.url = "nixpkgs/nixpkgs-unstable";

    home-manager = {
      url = "github:nix-community/home-manager/release-25.11";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nvim-config.url = "github:samov0619-prog/nvim";
    freesm = {
      url = "github:FreesmTeam/FreesmLauncher";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      nixpkgs-unstable,
      home-manager,
      nvim-config,
      freesm,
      ...
    }:
    let
      lib = nixpkgs.lib;

      systems = {
        linux = "x86_64-linux";
        mac = "aarch64-darwin";
      };

      pkgsFor =
        system:
        import nixpkgs {
          inherit system;
          overlays = (if system == systems.linux then [ self.overlays.filemanager1-common ] else [ ]) ++ [
            freesm.overlays.default
          ];
        };

      pkgsUnstableFor =
        system:
        import nixpkgs-unstable {
          inherit system;
        };

      mkHM =
        {
          system,
          username,
          modules,
        }:
        home-manager.lib.homeManagerConfiguration {
          pkgs = pkgsFor system;
          inherit modules;
          extraSpecialArgs = {
            inherit username nvim-config;
            pkgsUnstable = pkgsUnstableFor system;
          };
        };

      mkNixos =
        {
          system,
          modules,
        }:
        lib.nixosSystem {
          inherit system;
          modules = modules ++ [
            home-manager.nixosModules.home-manager
          ];
        };
    in
    {
      overlays.filemanager1-common = final: prev: {
        filemanager1-common = final.callPackage ./pkgs/filemanager1-common { };
      };

      nixosConfigurations = {
        desktop = mkNixos {
          system = systems.linux;
          modules = [
            ./hosts/desktop
          ];
        };
      };

      homeConfigurations = {
        samov-desktop = mkHM {
          system = systems.linux;
          username = "samov";
          modules = [
            ./home/users/samov

            ./home/core-set
            ./home/gui-set
            ./home/personal-set

            ./home/linux/desktop
          ];
        };

        samov-mac = mkHM {
          system = systems.mac;
          username = "samov";
          modules = [
            ./home/users/samov
            ./home/core-set
          ];
        };
      };
    };
}
