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
            inherit username nvim-config;
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
            ./home/personal-set

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
            ./home/personal-set

            ./home/linux/laptop
          ];
        };

        samov-server = mkHM {
          pkgs = pkgsFor systems.linux [ ];
          username = "samov";
          modules = [
            ./home/users/samov

            ./home/core-set
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
