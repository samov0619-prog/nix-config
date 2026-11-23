// Evaluate the same explicit source lists used by HM and standalone exports.
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const instructions = JSON.parse(
  execFileSync(
    "nix",
    [
      "eval",
      "--offline",
      "--json",
      "--file",
      fileURLToPath(new URL("../config/instructions.nix", import.meta.url)),
    ],
    { timeout: 10000 },
  ),
);
