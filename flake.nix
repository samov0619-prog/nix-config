# ── Новый хост на 26.05 (свежие стейты) ──────────────────────────────
# Fresh-инсталл ≠ бамп stateVersion на старом хосте: легаси-стейта нет,
# мигрировать нечего. stateVersion — PER-HOST, новый 26.05-хост спокойно
# живёт рядом с desktop/laptop на 25.11, совпадать им не нужно.
#
# Чек-лист при заведении нового ноута:
#
# 1. system.stateVersion — уже per-host (в hosts/<host>/default.nix).
#    В новом hosts/<newlaptop>/default.nix поставить "26.05".
#
# 2. home.stateVersion — СЕЙЧАС захардкожен ОБЩИМ в
#    home/users/samov/default.nix = "25.11" → новый хост унаследует
#    25.11, а не 26.05. Фикс (один раз):
#      а) в home/users/samov:  home.stateVersion = lib.mkDefault "25.11";
#      б) в модулях нового homeConfiguration добавить инлайн-оверрайд:
#           { home.stateVersion = "26.05"; }
#    Старые хосты без инлайна остаются на 25.11 (mkDefault не мешает).
#    Без mkDefault пришлось бы mkForce — грязно.
#
# 3. Пины yazi/firefox/hyprland-configType гейтятся по
#    (lib.versionOlder config.home.stateVersion "26.05") — на 26.05
#    условие ложно, пины НЕ применяются, хост берёт нативные дефолты
#    (y / lua / XDG-firefox). Трогать ничего не надо. Firefox сразу
#    стартует в $XDG_CONFIG_HOME/mozilla/firefox с чистого профиля —
#    переносить нечего, это fresh-инсталл.
#
# 4. hardware-configuration.nix генерить НА самой машине
#    (nixos-generate-config), НЕ копировать с laptop.
#
# 5. Общие модули (core-set/gui-set/linux/*) переиспользуются как есть.
#    freesm/extra-cmake-modules-блокер к stateVersion отношения не имеет
#    (если всплывёт — тот же фикс, что на laptop).
#
# Скелет нового блока:
#   nixosConfigurations.<newlaptop> = mkNixos {
#     system = systems.linux;
#     modules = [ ./hosts/<newlaptop> ];   # внутри: system.stateVersion = "26.05"
#   };
#   homeConfigurations.samov-<newlaptop> = mkHM {
#     pkgs = pkgsFor systems.linux [
#       self.overlays.filemanager1-common
#       freesm.overlays.default
#     ];
#     username = "samov";
#     modules = [
#       ./home/users/samov
#       { home.stateVersion = "26.05"; }   # оверрайд mkDefault-а 25.11
#       ./home/core-set
#       ./home/gui-set
#       ./home/personal-set
#       ./home/linux/<newlaptop>           # свой leaf или переиспользовать laptop
#     ];
#   };
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
