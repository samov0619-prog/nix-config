// Evaluate actual module outputs with package constructors left lazy/stubbed.
// This checks composition, not pinned Home Manager merging or realizations.
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export function homeWiring(
  enabled = true,
  isLinux = true,
  configHome = "/home/fixture/.config",
) {
  const module = fileURLToPath(new URL("../default.nix", import.meta.url));
  return JSON.parse(
    execFileSync(
      "nix",
      [
        "eval",
        "--offline",
        "--impure",
        "--json",
        "--expr",
        `
    let
      lib = {
        optionalAttrs = condition: attrs: if condition then attrs else {};
        hasPrefix = prefix: text: builtins.substring 0 (builtins.stringLength prefix) text == prefix;
      };
      module = import ${JSON.stringify(module)} {
        inherit lib;
        config.programs.opencode.todo.enable = ${enabled};
        config.home.homeDirectory = "/home/fixture";
        config.xdg.configHome = ${JSON.stringify(configHome)};
        pkgs.stdenv.isLinux = ${isLinux};
        opencodePackage = null;
      };
      files = module.xdg.configFile;
    in {
      base = module.programs.opencode.settings;
      baseText = files."opencode/AGENTS.md".text;
      personalFiles = builtins.listToAttrs (map (name: {
        name = builtins.substring 15 (-1) name;
        value = builtins.getAttr name files;
      }) (builtins.filter (name: lib.hasPrefix "opencode-local/" name) (builtins.attrNames files)));
      names = builtins.attrNames files;
      env = module.home.sessionVariables;
      skills = builtins.attrNames module.programs.opencode.skills;
    }`,
      ],
      { encoding: "utf8", timeout: 10000, maxBuffer: 4 * 1024 * 1024 },
    ),
  );
}
