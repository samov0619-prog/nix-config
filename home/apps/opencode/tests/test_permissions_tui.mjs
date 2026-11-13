import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { test } from "node:test";
import { pathToFileURL } from "node:url";

const tick = () => new Promise((resolve) => setImmediate(resolve));
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
};

test("HM keeps both permission modules in one TUI-only plugin directory", () => {
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
        `f: (f {
      pkgs = {
        stdenv.isLinux = true;
        formats.json = _: {};
        runCommand = name: attrs: script: { inherit name script; };
      };
      lib.optionalAttrs = condition: attrs: if condition then attrs else {};
      config = {}; opencodePackage = null;
    }).xdg.configFile."opencode/plugins/permissions".source`,
      ],
      { timeout: 10000 },
    ),
  );
  assert.equal(result.name, "opencode-permissions-plugin");
  for (const name of ["tui.tsx", "state.ts"]) {
    const source = result.script.match(
      new RegExp(`cp (\\S+) "\\$out/${name.replace(".", "\\.")}"`),
    )?.[1];
    assert.ok(source);
    assert.equal(
      readFileSync(source, "utf8"),
      readFileSync(
        new URL(`../plugins/permissions/${name}`, import.meta.url),
        "utf8",
      ),
    );
  }
  assert.doesNotMatch(result.script, /index\.ts|replaceVars/);
});

test(
  "actual TUI commands/controller with public API-shaped fixtures and lazy JSX",
  {
    skip:
      !process.env.OPENCODE_TEST_TYPESCRIPT &&
      "Set OPENCODE_TEST_TYPESCRIPT to an installed typescript.js (no installation).",
  },
  async () => {
    const ts = (
      await import(pathToFileURL(process.env.OPENCODE_TEST_TYPESCRIPT).href)
    ).default;
    const file = new URL("../plugins/permissions/tui.tsx", import.meta.url)
      .href;
    let host;
    globalThis.__permissionsFixture = {
      signal(value) {
        const signal = { value };
        host.signals.push(signal);
        return [
          () => signal.value,
          (next) => {
            signal.value = next;
          },
        ];
      },
      effect(fn) {
        host.effects.push(fn);
        fn();
      },
      cleanup(fn) {
        host.cleanups.push(fn);
      },
      dimensions: () => host.dimensions,
    };
    const loader = registerHooks({
      resolve(specifier, context, next) {
        const source =
          specifier === "solid-js"
            ? `
        export const createSignal = value => globalThis.__permissionsFixture.signal(value);
        export const createEffect = fn => globalThis.__permissionsFixture.effect(fn);
        export const onCleanup = fn => globalThis.__permissionsFixture.cleanup(fn);
        export const Show = props => props.when ? props.children : props.fallback;
        export const For = props => props.each.map((value, index) => props.children(value, () => index));
      `
            : specifier === "@opentui/solid"
              ? `
        export const useTerminalDimensions = () => globalThis.__permissionsFixture.dimensions;
      `
              : undefined;
        if (source)
          return {
            shortCircuit: true,
            url: "data:text/javascript," + encodeURIComponent(source),
          };
        return next(specifier, context);
      },
      load(url, context, next) {
        if (url !== file) return next(url, context);
        const result = ts.transpileModule(readFileSync(new URL(url), "utf8"), {
          fileName: "tui.tsx",
          reportDiagnostics: true,
          compilerOptions: {
            jsx: ts.JsxEmit.React,
            jsxFactory: "__jsx",
            module: ts.ModuleKind.ESNext,
            target: ts.ScriptTarget.ES2022,
          },
          // Preserve JSX getters, as Solid does. This is a view/API fixture,
          // not OpenTUI rendering, its dependency tracker or keyboard dispatch.
          transformers: {
            before: [
              (context) => {
                const f = context.factory;
                const visit = (node) => {
                  if (ts.isJsxExpression(node) && node.expression)
                    return f.updateJsxExpression(
                      node,
                      f.createCallExpression(
                        f.createIdentifier("__lazy"),
                        undefined,
                        [
                          f.createArrowFunction(
                            undefined,
                            undefined,
                            [],
                            undefined,
                            f.createToken(ts.SyntaxKind.EqualsGreaterThanToken),
                            ts.visitNode(node.expression, visit),
                          ),
                        ],
                      ),
                    );
                  return ts.visitEachChild(node, visit, context);
                };
                return (node) => ts.visitNode(node, visit);
              },
            ],
          },
        });
        assert.deepEqual(
          result.diagnostics,
          [],
          "actual TypeScript parser accepts TSX",
        );
        return {
          shortCircuit: true,
          format: "module",
          source:
            `
        const __lazy = read => ({ __lazy: read });
        const __read = value => value?.__lazy ? value.__lazy() : value;
        const __jsx = (type, input, ...children) => {
          const props = {};
          for (const [key, value] of Object.entries(input ?? {}))
            Object.defineProperty(props, key, { get: () => __read(value) });
          Object.defineProperty(props, 'children', { get: () => children.length === 1
            ? __read(children[0]) : children.map(__read) });
          return { type, props };
        };
      ` + result.outputText,
        };
      },
    });
    try {
      const { default: plugin, display } = await import(file);
      assert.equal(
        display("a\n\x1b[31m\x00\x7f"),
        "a\\u000a\\u001b[31m\\u0000\\u007f",
      );
      assert.equal(display("a\u202e\u2028\u2066"), "a\\u202e\\u2028\\u2066");
      const grant = (id, projectID = "project-a") => ({
        id,
        projectID,
        action: "shell",
        resource: "command " + id,
      });
      function fixture() {
        const state = {
          signals: [],
          effects: [],
          cleanups: [],
          layers: [],
          toasts: [],
          dimensions: { width: 80, height: 24 },
          route: { type: "session", sessionID: "ses_a" },
          session: {
            projectID: "project-a",
            location: { directory: "/project-a" },
          },
          entries: [grant("a"), grant("b"), grant("foreign", "project-b")],
          locations: [],
          lists: [],
          removed: [],
          shows: 0,
          clears: 0,
          root: undefined,
          onClose: undefined,
          scroll: {
            calls: [],
            scrollBy(n) {
              this.calls.push(n);
            },
            scrollTo(n) {
              this.calls.push([n]);
            },
          },
        };
        host = state;
        state.lookup = async () => ({ project: { id: "project-a" } });
        state.list = async () => state.entries;
        state.api = {
          client: {
            location: {
              get: async (input) => {
                state.locations.push(input);
                return state.lookup();
              },
            },
            permission: {
              saved: {
                list: async (input) => {
                  state.lists.push(input);
                  return state.list();
                },
                remove: async (input) => {
                  state.removed.push(input);
                  state.entries = state.entries.filter(
                    (entry) => entry.id !== input.id,
                  );
                },
              },
            },
          },
          data: {
            session: { get: () => state.session },
            location: { default: () => ({ directory: "/launch-directory" }) },
          },
          theme: { text: { base: "white", muted: "gray" } },
          keymap: {
            layer(factory) {
              const layer = factory();
              state.layers.push(layer);
              if (layer.mode === "modal")
                state.cleanups.push(() => {
                  state.layers = state.layers.filter(
                    (entry) => entry !== layer,
                  );
                });
            },
          },
          ui: {
            router: { current: () => state.route },
            toast: { show: (value) => state.toasts.push(value) },
            dialog: {
              set: (value) => {
                state.presentation = value;
              },
              show(render, close) {
                state.shows++;
                state.onClose = close;
                try {
                  const node = render();
                  assert.equal(
                    typeof node.props.current,
                    "function",
                    JSON.stringify(node.props.current),
                  );
                  state.root = node.type(node.props);
                } catch (error) {
                  state.renderError = error;
                  throw error;
                }
              },
              clear() {
                state.clears++;
                state.onClose?.();
                state.onClose = undefined;
                state.cleanups
                  .splice(0)
                  .reverse()
                  .forEach((fn) => fn());
                state.effects = [];
                state.root = undefined;
              },
            },
          },
        };
        state.dispose = plugin.setup(state.api);
        state.open = state.layers[0].commands[0].run;
        state.key = async (bind) => {
          const layer = state.layers.find((layer) => layer.mode === "modal");
          assert.ok(layer, "dialog owns a modal keymap");
          assert.equal(layer.priority, 20);
          await layer.commands.find((command) => command.bind === bind).run();
          await tick();
        };
        state.view = () => state.signals.at(-1).value;
        state.text = () => {
          const walk = (node) => {
            if (Array.isArray(node)) return node.map(walk).join("\n");
            if (typeof node === "string" || typeof node === "number")
              return String(node);
            if (!node) return "";
            if (typeof node.type === "function")
              return walk(node.type(node.props));
            node.props.ref?.(state.scroll);
            return walk(node.props.children);
          };
          return walk(state.root);
        };
        return state;
      }

      let state = fixture();
      assert.deepEqual(state.layers[0].commands[0].slash, {
        name: "permissions",
      });
      assert.equal(state.layers[0].commands[0].palette, true);
      await state.open();
      await tick();
      assert.equal(state.renderError, undefined);
      assert.deepEqual(state.locations, [
        { location: { directory: "/project-a" } },
      ]);
      assert.deepEqual(state.lists, [{ projectID: "project-a" }]);
      assert.deepEqual(state.presentation, { size: "large", centered: true });
      assert.match(state.text(), /Saved permissions.*\/project-a/s);
      assert.match(state.text(), /› shell · command a/);
      assert.doesNotMatch(state.text(), /foreign/);
      await state.open();
      assert.equal(state.shows, 1, "no duplicate open dialog");
      await state.key("ctrl+d");
      assert.match(state.text(), /Press Ctrl\+D again/);
      assert.deepEqual(state.removed, []);
      await state.key("pagedown");
      assert.equal(state.view().armed, undefined);
      assert.deepEqual(state.scroll.calls, [3]);
      await state.key("ctrl+d");
      await state.key("down");
      assert.equal(state.view().armed, undefined);
      assert.match(state.text(), /› shell · command b/);
      await state.key("ctrl+d");
      await state.key("ctrl+d");
      assert.deepEqual(state.removed, [{ id: "b" }]);
      assert.doesNotMatch(state.text(), /command b/);
      await state.key("q");
      assert.equal(state.layers.length, 1, "modal removed on close");
      await state.open();
      await tick();
      assert.equal(state.view().armed, undefined);
      await state.key("escape");
      state.dispose();

      // Closure while validating never sends DELETE, including q/Esc and reload.
      for (const close of [
        "q",
        "escape",
        "dispose",
        "scope",
        "identity",
        "replace",
      ]) {
        state = fixture();
        await state.open();
        await tick();
        await state.key("ctrl+d");
        const wait = deferred();
        state.list = () => wait.promise;
        const deleting = state.key("ctrl+d");
        if (close === "dispose") state.dispose();
        else if (close === "scope" || close === "identity") {
          state.session = {
            projectID: "project-b",
            location: {
              directory: close === "identity" ? "/project-a" : "/project-b",
            },
          };
          state.effects.slice().forEach((fn) => fn());
        } else if (close === "replace") {
          state.api.ui.dialog.clear(); // host calls onClose before replacement
          state.api.ui.dialog.clear = () =>
            assert.fail("must not close a replacement dialog");
        } else await state.key(close);
        wait.resolve(state.entries);
        await deleting;
        assert.deepEqual(state.removed, []);
        assert.equal(state.layers.length, 1);
        state.dispose();
      }

      state = fixture();
      const lookup = deferred();
      state.lookup = () => lookup.promise;
      const opening = state.open();
      await state.open();
      assert.equal(
        state.locations.length,
        1,
        "coalesces duplicate project lookup",
      );
      state.session = undefined;
      lookup.resolve({ project: { id: "project-a" } });
      await opening;
      assert.equal(state.shows, 0, "does not show a stale opening project");
      await state.open();
      assert.equal(
        state.locations.length,
        1,
        "does not fall back during session hydration",
      );
      assert.match(state.toasts.at(-1).message, /No permissions changed/);
      state.dispose();

      state = fixture();
      const lateLookup = deferred();
      state.lookup = () => lateLookup.promise;
      const lateOpening = state.open();
      state.dispose();
      lateLookup.resolve({ project: { id: "project-a" } });
      await lateOpening;
      assert.equal(
        state.shows,
        0,
        "plugin disposal prevents a late opening dialog",
      );
      assert.equal(state.toasts.length, 0);

      state = fixture();
      state.route = { type: "home" };
      state.api.location = { directory: "/explicit-project" };
      await state.open();
      await tick();
      assert.deepEqual(state.locations, [
        { location: { directory: "/explicit-project" } },
      ]);
      assert.match(state.text(), /\/explicit-project/);
      state.dispose();

      state = fixture();
      state.lookup = async () => {
        throw new Error("offline");
      };
      await state.open();
      assert.equal(state.shows, 0);
      assert.equal(state.toasts.length, 1);
      state.dispose();

      state = fixture();
      state.entries = [];
      await state.open();
      await tick();
      assert.match(state.text(), /No saved permissions for this project/);
      await state.key("ctrl+d");
      assert.deepEqual(state.removed, []);
      state.dispose();

      state = fixture();
      state.entries = Array.from({ length: 30 }, (_, i) =>
        grant(String(i).padStart(2, "0")),
      );
      state.entries[29].resource +=
        "\n\x1b[31m" + "very long resource ".repeat(100);
      await state.open();
      await tick();
      for (let i = 0; i < 29; i++) await state.key("down");
      assert.match(state.text(), /30\/30/);
      assert.match(state.text(), /\\u000a\\u001b/);
      assert.doesNotMatch(state.text(), /command 00/);
      assert.match(state.text(), /very long resource/);
      state.dispose();
    } finally {
      host?.dispose?.();
      loader.deregister();
      delete globalThis.__permissionsFixture;
    }
  },
);
