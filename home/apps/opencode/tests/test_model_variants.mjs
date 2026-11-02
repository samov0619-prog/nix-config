import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { join } from "node:path";
import { test } from "node:test";
import { canonicalModel } from "../plugins/model-routing/model-routing.ts";

// Apply the production patch stack and execute its real selection functions.
const directory = mkdtempSync("/tmp/opencode/model-variants-test-");
let source;
try {
  const upstream =
    process.env.OPENCODE_TEST_SOURCE ??
    execFileSync(
      "nix",
      [
        "eval",
        "--offline",
        "--raw",
        "path:.#packages.x86_64-linux.opencode.src",
      ],
      { encoding: "utf8" },
    ).trim();
  for (const relative of [
    "packages/tui/src/context/local.tsx",
    "packages/tui/src/component/dialog-model.tsx",
    "packages/core/src/session/runner/model.ts",
    "packages/core/src/session/context.ts",
    "packages/core/src/session/compaction.ts",
    "packages/core/src/session/generate.ts",
  ]) {
    const target = join(directory, relative);
    mkdirSync(join(target, ".."), { recursive: true });
    copyFileSync(join(upstream, relative), target);
    chmodSync(target, 0o600);
  }
  for (const patch of [
    "session-routing",
    "manual-model-routing",
    "model-variants",
  ]) {
    execFileSync(
      "patch",
      [
        "--batch",
        "--fuzz=0",
        "-s",
        "-p1",
        "-i",
        join(process.cwd(), `home/apps/opencode/patches/${patch}.patch`),
      ],
      { cwd: directory, encoding: "utf8" },
    );
  }
  source = readFileSync(
    join(directory, "packages/tui/src/context/local.tsx"),
    "utf8",
  );
} finally {
  rmSync(directory, { recursive: true, force: true });
}

test("persisted legacy aliases expose canonical model and explicit effort in TUI", () => {
  const code = stripTypeScriptTypes(
    source.slice(
      source.indexOf("      function durableSelection("),
      source.indexOf("      function sessionSelection("),
    ),
  );
  for (const [id, modelID, variant] of [
    ["gpt-6.1-sol-plan", "gpt-6.1-sol", "xhigh"],
    ["gpt-6.1-sol-high", "gpt-6.1-sol", "high"],
    ["gpt-6-luna-max", "gpt-6-luna", "max"],
  ]) {
    const model = { providerID: "openai", id, variant: "default" };
    const read = new Function(
      "data",
      "canonicalModel",
      "normalizeModelVariant",
      `${code}\nreturn durableSelection("session");`,
    );
    assert.deepEqual(
      read(
        { session: { get: () => ({ model }) } },
        canonicalModel,
        (value) => value,
      ),
      { providerID: "openai", modelID, variant },
    );
    assert.equal(
      model.id,
      id,
      "read compatibility must not mutate stored history",
    );
  }
});

test("Build and Plan select independent effort on the same model without role aliases", () => {
  const code = stripTypeScriptTypes(
    source.slice(
      source.indexOf("      function preferredSelection("),
      source.indexOf("      function durableSelection("),
    ),
  );
  for (const variant of ["high", "xhigh"]) {
    const select = new Function(
      "agent",
      "configuredModel",
      "preferences",
      "modelPreferenceKey",
      "normalizeModelVariant",
      "models",
      `${code}\nreturn preferredSelection({providerID:"openai",modelID:"gpt-6.1-sol"});`,
    );
    const selected = select(
      {
        current: () => ({
          model: { providerID: "openai", id: "gpt-6.1-sol", variant },
        }),
      },
      () => undefined,
      { variant: {} },
      (model) => `${model.providerID}/${model.modelID}`,
      (value) => value,
      () => [
        {
          providerID: "openai",
          id: "gpt-6.1-sol",
          variants: [{ id: "high" }, { id: "xhigh" }],
        },
      ],
    );
    assert.equal(selected.variant, variant);
  }
});
