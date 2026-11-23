// The same pure file/settings definitions intended for the later HM/Mac wiring.
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const personalLayers = (todoEnabled = true) =>
  JSON.parse(
    execFileSync(
      "nix",
      [
        "eval",
        "--offline",
        "--json",
        "--file",
        fileURLToPath(
          new URL("../config/personal-layers.nix", import.meta.url),
        ),
        "--apply",
        `f: f { todoEnabled = ${todoEnabled}; }`,
      ],
      { timeout: 10000, maxBuffer: 4 * 1024 * 1024 },
    ),
  );
