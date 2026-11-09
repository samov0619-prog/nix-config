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
    opencode.url = "github:anomalyco/opencode/v2.1.4";

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    browser-previews = {
      url = "github:nix-community/browser-previews";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Reserved for a future declarative Neovim deployment. Server Neovim is
    # manual today, so keep this input disabled to avoid fetching it.
    # nvim-config.url = "github:samov0619-prog/nvim";

    xremap-flake = {
      url = "github:xremap/nix-flake";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    freesm = {
      url = "github:FreesmTeam/FreesmLauncher";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nix-gc-env.url = "github:Julow/nix-gc-env";
    hermes-agent.url = "github:NousResearch/hermes-agent";
    # Real VPS values are selected with --override-input; never lock local paths.
    server-settings = {
      url = "path:./hosts/server/settings-template";
      flake = false;
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      nixpkgs-unstable,
      home-manager,
      browser-previews,
      disko,
      # nvim-config,
      freesm,
      nix-gc-env,
      xremap-flake,
      hermes-agent,
      opencode,
      server-settings,
      ...
    }:
    let
      lib = nixpkgs.lib;
      serverSettings = import "${server-settings}/settings.nix";

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

      browserPreviewsFor = system: browser-previews.packages.${system};

      mkHM =
        {
          pkgs,
          username,
          modules,
        }:
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs modules;
          extraSpecialArgs = {
            # To re-enable declarative Neovim, also pass nvim-config here.
            inherit username xremap-flake hermes-agent;
            pkgsUnstable = pkgsUnstableFor pkgs.stdenv.hostPlatform.system;
            browserPreviews = browserPreviewsFor pkgs.stdenv.hostPlatform.system;
            opencodePackage = self.packages.${pkgs.stdenv.hostPlatform.system}.opencode;
          };
        };

      mkNixos =
        {
          system,
          modules,
          overlays ? [ ],
          extraSpecialArgs ? { },
        }:
        lib.nixosSystem {
          inherit system;
          specialArgs = {
            pkgsUnstable = pkgsUnstableFor system;
          }
          // extraSpecialArgs;
          modules = [
            {
              nixpkgs.overlays = overlays;
            }
            ./hosts/profiles/gc.nix
          ]
          ++ modules
          ++ [
            home-manager.nixosModules.home-manager
            nix-gc-env.nixosModules.default
          ];
        };

      mkServerInstaller = lib.nixosSystem {
        system = systems.linux;
        specialArgs = { inherit serverSettings; };
        modules = [ ./hosts/server/installer.nix ];
      };
    in
    {
      # Same nixfmt and default flags as Neovim's nixd -> nixfmt command.
      formatter = lib.genAttrs (builtins.attrValues systems) (system: (pkgsFor system [ ]).nixfmt);

      packages.x86_64-linux.hypr-spaces = (pkgsFor systems.linux [ ]).callPackage ./pkgs/hypr-spaces { };
      packages.x86_64-linux.opencode = import ./home/apps/opencode/package.nix {
        upstream = opencode.packages.x86_64-linux.opencode;
        pkgs = pkgsFor systems.linux [ ];
      };
      packages.aarch64-darwin.opencode = import ./home/apps/opencode/package.nix {
        upstream = opencode.packages.aarch64-darwin.opencode;
        pkgs = pkgsFor systems.mac [ ];
      };

      overlays = {
        amnezia-vpn = final: prev: {
          amnezia-vpn = final.callPackage ./pkgs/amnezia-vpn { };
        };

        filemanager1-common = final: prev: {
          filemanager1-common = final.callPackage ./pkgs/filemanager1-common { };
        };
      };

      nixosConfigurations = {
        desktop = mkNixos {
          system = systems.linux;
          overlays = [ self.overlays.amnezia-vpn ];
          modules = [
            ./hosts/profiles/time.nix
            ./hosts/profiles/mdns.nix
            ./hosts/desktop
          ];
        };

        laptop = mkNixos {
          system = systems.linux;
          overlays = [ self.overlays.amnezia-vpn ];
          modules = [
            ./hosts/profiles/time.nix
            ./hosts/profiles/mdns.nix
            ./hosts/laptop
          ];
        };

        server = mkNixos {
          system = systems.linux;
          extraSpecialArgs = { inherit serverSettings; };
          modules = [
            disko.nixosModules.disko
            ./hosts/server
          ];
        };

        server-installer = mkServerInstaller;

        laptop-next = mkNixos {
          system = systems.linux;
          overlays = [ self.overlays.amnezia-vpn ];
          # Isolated graphics package set; NVIDIA needs unfree evaluation enabled.
          extraSpecialArgs.pkgsGraphics = import nixpkgs-unstable {
            system = systems.linux;
            config.allowUnfree = true;
          };
          modules = [
            ./hosts/profiles/time.nix
            ./hosts/profiles/mdns.nix
            disko.nixosModules.disko
            ./hosts/laptop-next
          ];
        };

        desktop-next = mkNixos {
          system = systems.linux;
          modules = [
            ./hosts/profiles/time.nix
            ./hosts/profiles/mdns.nix
            disko.nixosModules.disko
            ./hosts/desktop-next
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
            ./home/core-set/nix-authoring.nix
            ./home/core-set/devtools/git-maintenance.nix
            ./home/core-set/go.nix
            ./home/core-set/devtools/neovim-mason.nix
            ./home/core-set/devenv.nix
            ./home/core-set/native-build.nix
            ./home/core-set/treesitter.nix
            ./home/core-set/devtools/github.nix
            # Aider is no longer used; keep the module for an explicit opt-in.
            # ./home/apps/aider
            ./home/apps/opencode
            # Hermes временно отключён.
            # ./home/apps/hermes
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
            ./home/core-set/nix-authoring.nix
            ./home/core-set/devtools/git-maintenance.nix
            ./home/core-set/go.nix
            ./home/core-set/devtools/neovim-mason.nix
            ./home/core-set/devenv.nix
            ./home/core-set/native-build.nix
            ./home/core-set/treesitter.nix
            ./home/core-set/devtools/github.nix
            # Aider is no longer used; keep the module for an explicit opt-in.
            # ./home/apps/aider
            ./home/apps/opencode
            # Hermes временно отключён.
            # ./home/apps/hermes
            ./home/gui-set
            ./home/modules/minecraft/server
            ./home/apps/minecraft
            ./home/apps/creative.nix

            ./home/linux/laptop
          ];
        };

        samov-laptop-next = mkHM {
          pkgs = pkgsFor systems.linux [
            self.overlays.filemanager1-common
            freesm.overlays.default
          ];
          username = "samov";
          modules = [
            ./home/users/samov
            ./home/users/samov/state-26.05.nix
            ./home/core-set
            ./home/core-set/nix-authoring.nix
            ./home/core-set/devtools/git-maintenance.nix
            ./home/core-set/go.nix
            ./home/core-set/devtools/neovim-mason.nix
            ./home/core-set/devenv.nix
            ./home/core-set/native-build.nix
            ./home/core-set/treesitter.nix
            ./home/core-set/devtools/github.nix
            ./home/apps/opencode
            ./home/gui-set
            ./home/modules/minecraft/server
            # Instance/heap and backup preflight remain separate decisions.
            ./home/apps/creative.nix
            ./home/linux/laptop-next
          ];
        };

        samov-server = mkHM {
          pkgs = pkgsFor systems.linux [ ];
          username = "samov";
          modules = [
            ./home/users/samov
            ./home/users/samov/state-26.05.nix

            ./home/core-set
            ./home/core-set/native-build.nix
            ./home/core-set/treesitter.nix
            ./home/modules/minecraft/server
            ./home/linux/server
          ];
        };

        samov-mac = mkHM {
          pkgs = pkgsFor systems.mac [ ];
          username = "samov";
          modules = [
            ./home/users/samov
            ./home/modules/profile-gc
            ./home/core-set
            ./home/core-set/nix-authoring.nix
            ./home/core-set/devtools/git-maintenance.nix
            ./home/core-set/go.nix
            ./home/core-set/devtools/neovim-mason.nix
            ./home/core-set/devenv.nix
            ./home/core-set/native-build.nix
            ./home/core-set/treesitter.nix
            ./home/core-set/devtools/github.nix
            ./home/modules/voice-dictate
            ./home/modules/kitty
          ];
        };
      };
    };
}
