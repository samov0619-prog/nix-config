// Packaging contracts with metadata fixtures, not a build or full HM evaluation.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../../../", import.meta.url));
const read = (path) => readFileSync(`${root}/${path}`, "utf8");

test("both package outputs use upstream OpenCode and its own wrapper package set", () => {
  const flake = read("flake.nix");
  assert.match(flake, /opencode\.url = "github:anomalyco\/opencode\/v2\.4\.0"/);
  for (const system of ["linux", "mac"]) {
    assert.ok(
      flake.includes(
        `upstream = opencode.packages.\${systems.${system}}.opencode;`,
      ),
    );
    assert.ok(
      flake.includes(
        `pkgs = opencode.inputs.nixpkgs.legacyPackages.\${systems.${system}};`,
      ),
    );
  }
  const lock = JSON.parse(read("flake.lock"));
  const upstream = lock.nodes[lock.nodes[lock.root].inputs.opencode];
  assert.equal(upstream.locked.rev, "44aed4fd144611879046ae923c25541f913780ad");
  assert.equal(
    lock.nodes[upstream.inputs.nixpkgs].locked.rev,
    "e21fec321d73511849707a7585e4ea155ee4bf40",
  );
});

for (const linux of [true, false]) {
  test(`actual override preserves upstream hooks and postPatch closure (${linux ? "Linux" : "Darwin"})`, () => {
    const value = JSON.parse(
      execFileSync(
        "nix",
        [
          "eval",
          "--offline",
          "--impure",
          "--json",
          "--expr",
          `
      let package = import ${JSON.stringify(`${root}/home/apps/opencode/package.nix`)} {
        upstream = {
          version = "2.4.0+44aed4f";
          overrideAttrs = f: f {
            env = { OPENCODE_VERSION = "2.4.0+44aed4f"; KEEP = "native"; };
            patches = [ "native.patch" ];
            postPatch = "native-post-patch\\n";
            postInstall = "native-wayland-and-path-wrapper\\n";
            node_modules.override = args: { inherit args; recipe = "native"; };
          };
        };
        pkgs = {
          lib = {
            assertMsg = p: m: if p then true else throw m;
            hasPrefix = p: s: builtins.substring 0 (builtins.stringLength p) s == p;
            optionalString = p: s: if p then s else "";
            makeLibraryPath = builtins.concatStringsSep ":";
          };
          stdenv = {
            hostPlatform = { isLinux = ${linux}; system = "${linux ? "x86_64-linux" : "aarch64-darwin"}"; };
            cc.cc.lib = "fixture-libstdc++";
          };
          alsa-lib = "fixture-alsa";
          libpulseaudio = "fixture-pulse";
        };
      }; in {
        inherit (package) env postPatch postInstall node_modules;
        patches = map builtins.baseNameOf package.patches;
      }
    `,
        ],
        { encoding: "utf8", timeout: 10000 },
      ),
    );
    assert.deepEqual(value.env, {
      OPENCODE_CHANNEL: "prod",
      OPENCODE_VERSION: "2.4.0+44aed4f",
      KEEP: "native",
    });
    assert.equal(value.patches.length, 6);
    assert.equal(value.patches[0], "native.patch");
    assert.deepEqual(
      value.node_modules,
      {
        recipe: "native",
        args: {
          hash: linux
            ? "sha256-sdMjb/l8SIthDbBJO3VzpyoOL9auoFGjVb6HdlxkQGg="
            : "sha256-3d3c6tnTD/fTefdrxUACkLLqKeXDDijLg2cp3yhz67Q=",
        },
      },
      "only the hash argument changes, through the upstream dependency override",
    );
    assert.ok(value.postPatch.startsWith("native-post-patch\n"));
    for (const name of [
      "local-model-routing.ts",
      "routing-models.json",
      "session-attention.ts",
    ])
      assert.ok(value.postPatch.includes(name));
    assert.ok(
      value.postInstall.startsWith("native-wayland-and-path-wrapper\n"),
    );
    if (linux)
      assert.match(
        value.postInstall,
        /fixture-libstdc\+\+:fixture-alsa:fixture-pulse/,
      );
    else assert.equal(value.postInstall, "native-wayland-and-path-wrapper\n");
  });
}
