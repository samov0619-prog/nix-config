import "./plugin-loader.mjs";
import { registerHooks } from "node:module";

// Unit tests only: real Solid route/focus tracking still requires the opt-in PTY.
registerHooks({
  resolve(specifier, context, next) {
    if (specifier === "solid-js") return {
      shortCircuit: true,
      url: "data:text/javascript,export const createEffect = fn => fn();",
    };
    return next(specifier, context);
  },
});
