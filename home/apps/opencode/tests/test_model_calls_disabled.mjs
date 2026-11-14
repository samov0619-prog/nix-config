import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { test } from "node:test";

test("home disables the optional model logger but retains its source and task report", () => {
  const result = JSON.parse(
    execFileSync(
      "nix",
      [
        "eval",
        "--offline",
        "--json",
        "--file",
        new URL("../default.nix", import.meta.url).pathname,
        "--apply",
        `f: let
          module = f {
            pkgs = {
              stdenv.isLinux = true;
              formats.json = _: {};
              runCommand = name: attrs: script: { inherit name script; };
              writeShellApplication = attrs: attrs.name;
            };
            lib.optionalAttrs = condition: attrs: if condition then attrs else {};
            config = {}; opencodePackage = null;
          };
          files = module.xdg.configFile;
        in {
          logger = files."opencode/plugins/model-calls-v2";
          otherPlugins = builtins.map
            (path: (builtins.getAttr path files).enable or true)
            [ "opencode/plugins/git-offline-v2"
              "opencode/plugins/permission-stats-v2"
              "opencode/plugins/limits-v2"
              "opencode/plugins/permissions"
              "opencode/plugins/skill-stats-v2" ];
          packages = module.home.packages;
        }`,
      ],
      { timeout: 10000 },
    ),
  );
  assert.equal(result.logger.enable, false);
  assert.equal(result.logger.source.name, "opencode-model-calls-plugin");
  assert.match(result.logger.source.script, /model-calls\.ts/);
  assert.ok(result.otherPlugins.every(Boolean));
  assert.ok(result.packages.includes("opencode-task-report"));
});
