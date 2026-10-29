import { registerHooks } from "node:module";

// Only the declaration wrapper is substituted. Tests execute the real plugin
// setup against public V2 API-shaped fakes; runtime smoke uses the actual SDK.
registerHooks({ resolve(specifier, context, next) {
  if (specifier === "@opencode/plugin" || specifier === "@opencode/plugin/tui") {
    return { shortCircuit: true, url: "data:text/javascript,export const Plugin = {define: value => value};" };
  }
  if (specifier === "@sessionAttention@" || specifier === "../../session-attention") {
    return { shortCircuit: true, url: new URL("../patches/session-attention.ts", import.meta.url).href };
  }
  return next(specifier, context);
} });
