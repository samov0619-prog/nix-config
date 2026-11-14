import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";
const { default: plugin, display } =
  await import("../plugins/permissions/tui.ts");

const tick = () => new Promise((resolve) => setImmediate(resolve));
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
};
const grant = (id, projectID = "project-a") => ({
  id,
  projectID,
  action: "shell",
  resource: "command " + id,
});

function fixture() {
  const state = {
    route: { type: "session", sessionID: "ses_a" },
    session: { projectID: "project-a", location: { directory: "/project-a" } },
    entries: [grant("a"), grant("b"), grant("foreign", "project-b")],
    locations: [],
    lists: [],
    removed: [],
    dialogs: [],
    layers: [],
    toasts: [],
    clears: 0,
    active: undefined,
  };
  state.lookup = async () => ({ project: { id: "project-a" } });
  state.list = async () => state.entries;
  state.remove = async (id) => {
    state.entries = state.entries.filter((entry) => entry.id !== id);
  };
  // Match native promise settlement: choose resolves once, then clear invokes
  // onClose synchronously; replacement settles the old dialog with undefined.
  const clear = () => {
    state.clears++;
    const dialog = state.active;
    state.active = undefined;
    dialog?.finish(undefined);
  };
  const show = (kind, options) => {
    if (state.active) clear();
    const wait = deferred();
    let settled = false;
    const dialog = {
      kind,
      options,
      finish(value) {
        if (settled) return;
        settled = true;
        wait.resolve(value);
      },
    };
    state.active = dialog;
    state.dialogs.push(dialog);
    return wait.promise;
  };
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
            return state.remove(input.id);
          },
        },
      },
    },
    data: {
      session: { get: () => state.session },
      location: { default: () => ({ directory: "/launch-directory" }) },
    },
    keymap: {
      layer(factory) {
        state.layers.push(factory());
      },
    },
    ui: {
      router: { current: () => state.route },
      toast: { show: (value) => state.toasts.push(value) },
      dialog: {
        select: (options) => show("select", options),
        confirm: (options) => show("confirm", options),
        clear,
        // No custom show(), renderer, theme, dimensions or JSX available.
      },
    },
  };
  state.dispose = plugin.setup(state.api);
  state.open = state.layers[0].commands[0].run;
  state.action = async (bind, id) => {
    assert.equal(state.active?.kind, "select");
    state.active.options.actions
      .find((action) => action.bind === bind)
      .onTrigger(id);
    await tick();
  };
  state.answer = async (value) => {
    assert.ok(state.active);
    state.active.finish(value);
    clear();
    await tick();
  };
  state.replace = () => {
    show("unrelated", {});
  };
  return state;
}

test("HM co-locates plain TypeScript modules; no JSX, private UI imports or UI patch", () => {
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
      pkgs = { stdenv.isLinux = true; formats.json = _: {};
        runCommand = name: attrs: script: { inherit name script; }; };
      lib.optionalAttrs = condition: attrs: if condition then attrs else {};
      config = {}; opencodePackage = null;
    }).xdg.configFile."opencode/plugins/permissions".source`,
      ],
      { timeout: 10000 },
    ),
  );
  assert.equal(result.name, "opencode-permissions-plugin");
  for (const name of ["tui.ts", "state.ts"]) {
    const source = result.script.match(
      new RegExp(`cp (\\S+) "\\$out/${name.replace(".", "\\.")}"`),
    )?.[1];
    assert.ok(source);
    const content = readFileSync(
      new URL(`../plugins/permissions/${name}`, import.meta.url),
      "utf8",
    );
    assert.equal(readFileSync(source, "utf8"), content);
    assert.doesNotMatch(
      content,
      /@opentui|solid-js|dialog\.show|<box|<text|scrollbox/,
    );
  }
  assert.doesNotMatch(result.script, /index\.ts|tui\.tsx|replaceVars/);
  assert.equal(
    display("a\n\x1b[31m\x00\x7f\u202e"),
    "a\\u000a\\u001b[31m\\u0000\\u007f\\u202e",
  );
});

test("Allowed permissions uses the native palette and only the renamed slash command", () => {
  const state = fixture();
  const commands = state.layers.flatMap((layer) => layer.commands);
  assert.equal(commands.length, 1);
  assert.equal(commands[0].title, "Allowed permissions");
  assert.equal(commands[0].palette, true);
  assert.deepEqual(commands[0].slash, { name: "allowed-permissions" });
  assert.equal(state.dialogs.length, 0);
  state.dispose();
});

test("native select -> native confirm -> selected ID removal; one key only requests confirmation", async () => {
  const state = fixture();
  const operation = state.open();
  await tick();
  assert.deepEqual(state.locations, [
    { location: { directory: "/project-a" } },
  ]);
  assert.deepEqual(state.lists, [{ projectID: "project-a" }]);
  assert.equal(state.active.kind, "select");
  assert.equal(state.active.options.title, "Saved permissions for project-a");
  assert.deepEqual(state.active.options.options, [
    { title: "command a", category: "shell", value: "a" },
    { title: "command b", category: "shell", value: "b" },
  ]);
  await state.open();
  assert.equal(
    state.dialogs.length,
    1,
    "duplicate commands do not open another list",
  );
  const oldAction = state.active.options.actions[0];
  await state.action("ctrl+d", "b");
  assert.equal(state.active.kind, "confirm");
  assert.match(state.active.options.message, /shell · command b/);
  assert.deepEqual(state.active.options.label, {
    confirm: "Remove",
    cancel: "Cancel",
  });
  assert.deepEqual(state.removed, []);
  oldAction.onTrigger("a");
  assert.equal(
    state.active.kind,
    "confirm",
    "stale list action cannot clear confirmation",
  );
  await state.answer(true);
  await operation;
  assert.deepEqual(state.removed, [{ id: "b" }]);
  assert.equal(
    state.active,
    undefined,
    "no unsolicited reopening after deletion",
  );
  assert.equal(state.toasts.at(-1).variant, "success");
  const again = state.open();
  await tick();
  assert.deepEqual(
    state.active.options.options.map((entry) => entry.value),
    ["a"],
  );
  await state.action("q");
  await again;
  state.dispose();
});

test("Enter chooses a grant; false, Escape and replacement never authorize deletion", async () => {
  for (const decision of [false, undefined, "replace"]) {
    const state = fixture();
    const operation = state.open();
    await tick();
    await state.answer("a");
    assert.equal(state.active.kind, "confirm");
    if (decision === "replace") state.replace();
    else await state.answer(decision);
    await operation;
    assert.deepEqual(state.removed, []);
    assert.equal(state.dialogs.length, decision === "replace" ? 3 : 2);
    if (decision === "replace") assert.equal(state.active.kind, "unrelated");
    state.dispose();
  }
});

test("q, Escape or another dialog closes the native list without confirmation", async () => {
  for (const close of ["q", "escape", "replace"]) {
    const state = fixture();
    const operation = state.open();
    await tick();
    if (close === "q") await state.action("q");
    else if (close === "replace") state.replace();
    else await state.answer(undefined);
    await operation;
    assert.deepEqual(state.removed, []);
    assert.equal(
      state.dialogs.some((dialog) => dialog.kind === "confirm"),
      false,
    );
    state.dispose();
  }
});

test("frozen project scope and plugin disposal refuse stale list/confirmation decisions", async () => {
  for (const phase of ["select", "confirm", "validation"]) {
    for (const change of ["directory", "identity", "dispose"]) {
      const state = fixture();
      const operation = state.open();
      await tick();
      if (phase !== "select") await state.action("ctrl+d", "a");
      const wait = deferred();
      if (phase === "validation") {
        state.list = () => wait.promise;
        await state.answer(true);
      }
      if (change === "dispose") {
        const close =
          phase === "select" ? state.active.options.actions[1] : undefined;
        const clears = state.clears;
        state.dispose();
        close?.onTrigger();
        assert.equal(
          state.clears,
          clears,
          "disposed callbacks do not clear a native dialog",
        );
      } else
        state.session = {
          projectID: "project-b",
          location: {
            directory: change === "identity" ? "/project-a" : "/project-b",
          },
        };
      if (phase === "select") await state.answer("a");
      else if (phase === "confirm") await state.answer(true);
      else {
        state.replace();
        wait.resolve(state.entries);
      }
      await operation;
      assert.deepEqual(state.removed, []);
      if (phase === "validation") assert.equal(state.active.kind, "unrelated");
      state.dispose();
    }
  }
});

test("pending lookup/load never opens a stale project; unloaded sessions have no launch fallback", async () => {
  for (const phase of ["lookup", "load"]) {
    const state = fixture();
    const wait = deferred();
    if (phase === "lookup") state.lookup = () => wait.promise;
    else state.list = () => wait.promise;
    const operation = state.open();
    await tick();
    state.session = undefined;
    wait.resolve(
      phase === "lookup" ? { project: { id: "project-a" } } : state.entries,
    );
    await operation;
    assert.equal(state.dialogs.length, 0);
    const lookups = state.locations.length;
    await state.open();
    assert.equal(state.locations.length, lookups);
    assert.match(state.toasts.at(-1).message, /operation failed/);
    state.dispose();
  }
});

test("errors use native toast, empty/home scopes and full escaped confirmation payloads", async () => {
  for (const failing of ["lookup", "list", "remove", "notify"]) {
    const state = fixture();
    if (failing === "notify") {
      state.api.ui.toast.show = (value) => {
        if (value.variant === "success") throw new Error("private detail");
        state.toasts.push(value);
      };
    } else
      state[failing] = async () => {
        throw new Error("private detail");
      };
    const operation = state.open();
    await tick();
    if (failing === "remove" || failing === "notify") {
      await state.action("ctrl+d", "a");
      await state.answer(true);
    }
    await operation;
    assert.equal(state.toasts.at(-1).variant, "error");
    assert.doesNotMatch(state.toasts.at(-1).message, /private detail/);
    if (failing === "notify") {
      assert.deepEqual(state.removed, [{ id: "a" }]);
      assert.match(state.toasts.at(-1).message, /check its current state/);
      assert.doesNotMatch(state.toasts.at(-1).message, /No deletion/);
    }
    assert.equal(state.active, undefined);
    state.dispose();
  }
  const state = fixture();
  state.route = { type: "home" };
  state.api.location = { directory: "/explicit-project" };
  state.entries = [];
  let operation = state.open();
  await tick();
  assert.deepEqual(state.locations, [
    { location: { directory: "/explicit-project" } },
  ]);
  assert.equal(state.active.options.options.length, 0);
  assert.match(state.active.options.placeholder, /No saved permissions/);
  await state.action("q");
  await operation;
  state.entries = [grant("a")];
  state.entries[0].resource += "\n\x1b[31m" + "long pattern ".repeat(100);
  operation = state.open();
  await tick();
  await state.answer("a");
  assert.ok(
    state.active.options.message.includes(display(state.entries[0].resource)),
    "confirmation receives the full escaped pattern, not a clipped prefix",
  );
  await state.answer(false);
  await operation;
  state.dispose();
});

test("late deletion response never overwrites another native dialog", async () => {
  const state = fixture();
  const operation = state.open();
  await tick();
  await state.action("ctrl+d", "a");
  const wait = deferred();
  state.remove = () => wait.promise;
  await state.answer(true);
  assert.deepEqual(state.removed, [{ id: "a" }]);
  state.replace();
  const clears = state.clears;
  state.dispose();
  wait.resolve();
  await operation;
  assert.equal(state.active.kind, "unrelated");
  assert.equal(state.clears, clears);
  assert.equal(state.lists.length, 2, "no refresh after disposal");
  assert.equal(state.toasts.length, 0);
});
