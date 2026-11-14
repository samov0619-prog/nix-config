import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

test("native HM target rename preserves the merged config and leaves only JSONC", () => {
  const repo = fileURLToPath(new URL("../../../../", import.meta.url));
  const module = fileURLToPath(new URL("../default.nix", import.meta.url));
  // Evaluate the actual pinned HM modules; comparing derivation paths does not
  // build/read the generated JSON or run activation. Both opt-in states matter:
  // decision-support adds settings through programs.opencode, not this leaf.
  const result = JSON.parse(
    execFileSync(
      "nix",
      [
        "eval",
        "--offline",
        "--impure",
        "--json",
        "--expr",
        `let
          flake = builtins.getFlake ${JSON.stringify(repo)};
          pkgs = import flake.inputs.nixpkgs { system = builtins.currentSystem; };
          currentModule = import ${JSON.stringify(module)};
          previousModule = { pkgs, lib, config, opencodePackage, ... }@args:
            let m = currentModule args;
            in m // { xdg = m.xdg // { configFile = m.xdg.configFile // {
              "opencode/opencode.json" = builtins.removeAttrs
                m.xdg.configFile."opencode/opencode.json" [ "target" ];
            }; }; };
          evaluate = implementation: enabled:
            (flake.inputs.home-manager.lib.homeManagerConfiguration {
              inherit pkgs;
              extraSpecialArgs.opencodePackage = pkgs.emptyDirectory.overrideAttrs (_: {
                pname = "opencode-fixture";
                version = "2.1.4";
              });
              modules = [ implementation ({ lib, ... }: {
                home.username = "opencode-fixture";
                home.homeDirectory = "/home/opencode-fixture";
                home.stateVersion = "26.05";
                programs.opencode.extraPackages = lib.mkForce [];
                programs.opencode.decisionSupport.enable = lib.mkForce enabled;
              }) ];
            }).config;
          targets = c: builtins.map (file: file.target)
            (builtins.filter (file: file.enable) (builtins.attrValues c.home.file));
          old = ".config/opencode/opencode.json";
          new = ".config/opencode/opencode.jsonc";
        in builtins.map (enabled:
          let before = evaluate previousModule enabled;
              after = evaluate currentModule enabled;
              beforeTargets = targets before;
              afterTargets = targets after;
          in {
            inherit enabled;
            beforeConfigTargets = builtins.filter (p: p == old || p == new) beforeTargets;
            afterConfigTargets = builtins.filter (p: p == old || p == new) afterTargets;
            otherTargetsUnchanged =
              builtins.filter (p: p != old) beforeTargets ==
              builtins.filter (p: p != new) afterTargets;
            sourceUnchanged =
              toString before.xdg.configFile."opencode/opencode.json".source ==
              toString after.xdg.configFile."opencode/opencode.json".source;
            settingsUnchanged = before.programs.opencode.settings == after.programs.opencode.settings;
            instructions = after.programs.opencode.settings.instructions or [];
          }
        ) [ false true ]`,
      ],
      { timeout: 30000 },
    ),
  );
  for (const state of result) {
    assert.deepEqual(state.beforeConfigTargets, [
      ".config/opencode/opencode.json",
    ]);
    assert.deepEqual(state.afterConfigTargets, [
      ".config/opencode/opencode.jsonc",
    ]);
    assert.equal(state.otherTargetsUnchanged, true);
    assert.equal(state.sourceUnchanged, true);
    assert.equal(state.settingsUnchanged, true);
    assert.equal(
      state.instructions.includes(
        "/home/opencode-fixture/.config/opencode/decision-support.md",
      ),
      state.enabled,
    );
  }
});
