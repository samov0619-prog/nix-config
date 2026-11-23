import "./plugin-loader.mjs";
import { registerHooks } from "node:module";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { test } from "node:test";

const visibleText = (node) =>
  Array.isArray(node)
    ? node.map(visibleText).join("")
    : typeof node === "string"
      ? node
      : node && typeof node === "object"
        ? visibleText(node.children)
        : "";
const nodes = (node) =>
  Array.isArray(node)
    ? node.flatMap(nodes)
    : node && typeof node === "object"
      ? [node, ...nodes(node.children)]
      : [];

test(
  "TUI public-API fixture: persistent indicator, no Git, manual commands and cleanup",
  {
    skip:
      !process.env.OPENCODE_TEST_TYPESCRIPT &&
      "Set OPENCODE_TEST_TYPESCRIPT to an installed typescript.js (no dependency installation).",
  },
  async () => {
    const ts = (
      await import(pathToFileURL(process.env.OPENCODE_TEST_TYPESCRIPT).href)
    ).default;
    const file = new URL("../plugins/limits/tui.tsx", import.meta.url).href;
    const loader = registerHooks({
      resolve(specifier, context, next) {
        if (specifier === "solid-js")
          return {
            shortCircuit: true,
            url:
              "data:text/javascript," +
              encodeURIComponent(
                "export const createSignal = value => [() => value, next => { value = next }]; export const Show = props => props.when ? props.children : props.fallback;",
              ),
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
        });
        assert.deepEqual(
          result.diagnostics,
          [],
          "real TypeScript parser accepts TSX",
        );
        return {
          format: "module",
          shortCircuit: true,
          source:
            "const __jsx = (type, props, ...children) => typeof type === 'function' ? type({...props, children: children[0]}) : ({type, props, children});\n" +
            result.outputText,
        };
      },
    });
    let cleanup;
    const originalInterval = globalThis.setInterval;
    let minuteClock;
    try {
      const { default: plugin } = await import(file);
      const commands = new Map();
      const slots = [];
      const listeners = new Map();
      const metadata = {
        "local.checkpoint": { ready: false },
        unrelated: "keep",
      };
      let cachedMetadata = { ...metadata };
      let route = { type: "session", sessionID: "ses_ui" };
      const messages = new Map();
      const serverMessages = new Map();
      let messageSyncs = 0;
      const messageInvalidations = [];
      const callback = () => listeners.get("rpc.local.limits.updated")?.({});
      const metadataCallback = (event) =>
        listeners.get("session.metadata.updated")?.(event);
      const connected = () => listeners.get("server.connected")?.({});
      const configUpdated = () => listeners.get("config.updated")?.({});
      let confirmed = false,
        resets = 0,
        statusCalls = 0;
      let metadataSyncs = 0;
      let prompts = [],
        stopped = 0,
        removed = 0;
      let holdStatus = false,
        releaseStatus;
      let statusValue = { available: false, active: 0 };
      let configValue = [];
      let configCalls = 0;
      let failConfig = false;
      let holdConfig = false,
        releaseConfig;
      const api = {
        client: {
          config: {
            async get(input) {
              assert.deepEqual(input, { location: { directory: "/no-git" } });
              configCalls++;
              const entries = configValue;
              if (holdConfig)
                await new Promise((resolve) => {
                  releaseConfig = resolve;
                });
              if (failConfig) throw new Error("Config unavailable");
              return entries;
            },
          },
          rpc() {
            return {
              async status() {
                statusCalls++;
                if (holdStatus)
                  await new Promise((resolve) => {
                    releaseStatus = resolve;
                  });
                return statusValue;
              },
              async reset() {
                resets++;
                return { reset: true };
              },
              events: {
                on() {
                  assert.fail(
                    "one-shot RPC subscriptions do not survive disconnects",
                  );
                },
              },
            };
          },
          session: {
            async prompt(input) {
              prompts.push(input);
            },
            async get() {
              return { metadata: { ...metadata } };
            },
            async update(input) {
              Object.assign(metadata, input.metadata);
            },
          },
        },
        data: {
          location: { default: () => ({ directory: "/no-git" }) },
          session: {
            get: () => ({ metadata: cachedMetadata }),
            message: {
              list: (id) => messages.get(id) ?? [],
              invalidate(id) {
                messageInvalidations.push(id);
              },
              async sync(id) {
                messageSyncs++;
                messages.set(id, structuredClone(serverMessages.get(id) ?? []));
              },
            },
            invalidate() {},
            async sync() {
              metadataSyncs++;
              cachedMetadata = { ...metadata };
            },
          },
          on(name, fn) {
            listeners.set(name, fn);
            return () => {
              stopped++;
              listeners.delete(name);
            };
          },
        },
        theme: {
          text: {
            muted: "gray",
            feedback: {
              info: { muted: "blue-muted", base: "blue" },
              success: { muted: "green-muted" },
            },
          },
        },
        ui: {
          router: { current: () => route },
          slot(claim) {
            slots.push(claim);
            return () => {
              removed++;
            };
          },
          dialog: {
            async confirm() {
              return confirmed;
            },
          },
          toast: { show() {} },
        },
        keymap: {
          layer(factory) {
            for (const command of factory().commands)
              commands.set(command.slash.name, command);
          },
        },
      };
      globalThis.setInterval = (callback, milliseconds, ...args) => {
        assert.equal(milliseconds, 60_000);
        minuteClock = callback;
        return originalInterval(callback, milliseconds, ...args);
      };
      cleanup = plugin.setup(api);
      globalThis.setInterval = originalInterval;
      await new Promise((resolve) => setImmediate(resolve));
      assert.equal(
        statusCalls,
        1,
        "initial status does not need a user/model request",
      );
      assert.equal(slots.length, 2, "home and session indicator");
      assert.equal(configCalls, 1);
      for (const slot of slots)
        assert.equal(
          visibleText(slot.render()).split("≋").length - 1,
          1,
          "native auto default renders exactly one icon",
        );
      const compactionIcon = () =>
        nodes(slots[1].render()).find(
          (node) => node.type === "text" && visibleText(node).trim() === "≋",
        );
      assert.equal(compactionIcon().props.fg, "gray");
      for (const status of ["running", "completed", "running", "failed"]) {
        // Simulate the host's public cache projection, not a second plugin
        // lifecycle; native event→cache integration is outside this mock.
        messages.set("ses_ui", [{ type: "compaction", status }]);
        assert.equal(
          compactionIcon().props.fg,
          status === "running" ? "blue" : "gray",
          `native ${status} state controls the same icon`,
        );
        assert.equal(visibleText(slots[1].render()).split("≋").length - 1, 1);
      }
      messages.set("ses_ui", [
        { type: "compaction", status: "running" },
        { type: "compaction", status: "completed" },
        { type: "assistant", content: [] },
      ]);
      assert.equal(compactionIcon().props.fg, "gray", "latest attempt wins");
      messages.set("another-session", [
        { type: "compaction", status: "running" },
      ]);
      assert.equal(
        compactionIcon().props.fg,
        "gray",
        "other sessions are ignored",
      );
      route = { type: "session", sessionID: "another-session" };
      assert.equal(
        compactionIcon().props.fg,
        "blue",
        "tab switch follows its cache",
      );
      route = { type: "home" };
      assert.equal(
        compactionIcon().props.fg,
        "gray",
        "home has no active session",
      );
      route = { type: "session", sessionID: "ses_ui" };
      messages.set("ses_ui", []);
      assert.equal(
        messageSyncs,
        0,
        "normal rendering adds no message requests",
      );
      for (const [entries, enabled] of [
        [
          [
            { type: "document", info: { compaction: { auto: false } } },
            { type: "directory", path: "/project/.opencode" },
            { type: "document", info: { compaction: { background: true } } },
            { type: "document", info: { compaction: { buffer: 32000 } } },
          ],
          false,
        ],
        [
          [
            { type: "document", info: { compaction: { auto: false } } },
            { type: "document", info: { compaction: { auto: true } } },
          ],
          true,
        ],
        [
          [{ type: "document", info: { compaction: { background: false } } }],
          true,
        ],
      ]) {
        configValue = entries;
        configUpdated();
        await new Promise((resolve) => setImmediate(resolve));
        for (const slot of slots)
          assert.equal(visibleText(slot.render()).includes("≋"), enabled);
      }
      failConfig = true;
      configUpdated();
      await new Promise((resolve) => setImmediate(resolve));
      for (const slot of slots)
        assert.doesNotMatch(
          visibleText(slot.render()),
          /≋/,
          "failed config reads must not claim auto is enabled",
        );
      failConfig = false;
      configValue = [];
      configUpdated();
      await new Promise((resolve) => setImmediate(resolve));
      const configBeforeIdle = configCalls;
      minuteClock();
      await new Promise((resolve) => setImmediate(resolve));
      assert.equal(
        statusCalls,
        1,
        "idle countdown does not poll the server/provider",
      );
      assert.equal(configCalls, configBeforeIdle, "no idle config polling");
      assert.equal(messageSyncs, 0, "no idle message polling");
      const pending = slots[1].render();
      assert.match(visibleText(pending), /unavailable/);
      assert.doesNotMatch(visibleText(pending), /Limits|Checkpoint|week/);
      assert.match(JSON.stringify(pending), /blue-muted/);
      assert.match(JSON.stringify(pending), /\+/);
      assert.doesNotMatch(JSON.stringify(pending), /⚠|\/checkpoint/);
      const beforeReconnect = statusCalls;
      const configBeforeReconnect = configCalls;
      // Simulate a transport gap: no updated/metadata event was delivered.
      // The native host stream reconnects without re-running plugin setup.
      statusValue = { available: false, active: 3 };
      configValue = [
        { type: "document", info: { compaction: { auto: false } } },
      ];
      configUpdated();
      await new Promise((resolve) => setImmediate(resolve));
      messages.set("ses_ui", [
        { type: "compaction", status: "running", reason: "manual" },
      ]);
      assert.equal(
        compactionIcon().props.fg,
        "blue",
        "manual compaction is visible even with auto disabled",
      );
      serverMessages.set("ses_ui", [
        { type: "compaction", status: "completed", reason: "manual" },
      ]);
      metadata["local.checkpoint"] = { ready: true };
      assert.doesNotMatch(visibleText(slots[1].render()), /✓/);
      connected();
      await new Promise((resolve) => setImmediate(resolve));
      assert.equal(statusCalls, beforeReconnect + 1);
      assert.equal(configCalls, configBeforeReconnect + 2);
      assert.equal(messageSyncs, 1);
      assert.deepEqual(messageInvalidations, ["ses_ui"]);
      assert.doesNotMatch(visibleText(slots[1].render()), /≋/);
      assert.equal(
        metadataSyncs,
        1,
        "reconnect refreshes missed checkpoint state",
      );
      assert.match(visibleText(slots[1].render()), /Active: 3/);
      assert.match(visibleText(slots[1].render()), /✓/);
      statusValue = { available: false, active: 1 };
      callback();
      await new Promise((resolve) => setImmediate(resolve));
      assert.match(visibleText(slots[1].render()), /Active: 1/);
      metadata["local.checkpoint"] = { ready: false };
      await metadataCallback({ data: { sessionID: "another-session" } });
      assert.equal(metadataSyncs, 1, "ignore other sessions' metadata events");
      const sharingStatus = {
        available: false,
        reason: "token-sharing-quota-unavailable",
        active: 2,
        mode: "normal",
        windowModes: {},
        thresholds: [],
        snapshot: null,
      };
      statusValue = sharingStatus;
      callback();
      await new Promise((resolve) => setImmediate(resolve));
      for (const slot of slots) {
        const sharing = visibleText(slot.render());
        assert.match(sharing, /not exposed by token sharing/);
        assert.match(sharing, /Active: 2/);
        assert.doesNotMatch(sharing, /Limits|Checkpoint|week/);
        assert.doesNotMatch(sharing, /unavailable|%|⚠|as of/);
      }
      for (const [primary, weekly] of [
        ["normal", "normal"],
        ["warn", "normal"],
        ["normal", "warn"],
        ["wrap", "normal"],
        ["normal", "wrap"],
        ["warn", "wrap"],
        ["wrap", "warn"],
        ["wrap", "wrap"],
      ]) {
        statusValue = {
          available: true,
          active: 2,
          // Deliberately fixed: markers must follow each window, not this aggregate.
          mode: "wrap",
          windowModes: { primary_window: primary, secondary_window: weekly },
          snapshot: {
            observedAt: Date.now(),
            windows: [
              {
                key: "primary_window",
                seconds: 18000,
                remaining:
                  primary === "normal" ? 80 : primary === "warn" ? 30 : 20,
                resetAt: Date.now() / 1000 + 3600,
              },
              {
                key: "secondary_window",
                seconds: 604800,
                remaining: weekly === "normal" ? 80 : weekly === "warn" ? 4 : 3,
                resetAt: Date.now() / 1000 + 3600,
              },
            ],
          },
        };
        callback();
        await new Promise((resolve) => setImmediate(resolve));
        const rendered = slots[1].render();
        const text = visibleText(rendered);
        assert.doesNotMatch(text, /Limits|Checkpoint|week|token sharing/);
        assert.match(text, /5h .* · \d+% /);
        assert.doesNotMatch(text, /wrap-up|stopping point|\/checkpoint/);
        const groups = nodes(rendered).filter(
          (node) =>
            node.type === "span" &&
            node.children.some(
              (child) => typeof child === "string" && child.includes("% "),
            ),
        );
        assert.equal(groups.length, 2, "both windows keep independent groups");
        for (const [index, [label, mode]] of [
          ["5h", primary],
          ["week", weekly],
        ].entries()) {
          const group = groups[index];
          assert.ok(group, `${label} has its own inline group`);
          const markers = nodes(group).filter(
            (node) =>
              node.type === "span" &&
              node.props?.style &&
              visibleText(node).includes("⚠"),
          );
          assert.equal(
            markers.length,
            mode === "normal" ? 0 : 1,
            `${label}: ${mode}`,
          );
          if (markers.length) {
            assert.equal(
              markers[0].props.style.fg,
              mode === "wrap" ? "#e5c07b" : "gray",
            );
            assert.match(
              visibleText(group),
              /% ⚠ ↻/,
              "triangle is next to this window's percentage",
            );
          }
        }
        assert.equal(
          prompts.length,
          0,
          "budget updates never send model prompts",
        );
      }
      metadata["local.checkpoint"] = { ready: true };
      await metadataCallback({ data: { sessionID: "ses_ui" } });
      assert.match(JSON.stringify(slots[1].render()), /green-muted/);
      assert.match(JSON.stringify(slots[1].render()), /✓/);
      assert.match(
        JSON.stringify(slots[1].render()),
        /⚠/,
        "checkpoint readiness does not dismiss budget warnings",
      );
      statusValue = sharingStatus;
      callback();
      await new Promise((resolve) => setImmediate(resolve));
      const switched = visibleText(slots[1].render());
      assert.match(switched, /not exposed by token sharing/);
      assert.match(switched, /✓/);
      assert.doesNotMatch(switched, /%|⚠|as of/);
      await commands.get("checkpoint-reset").run();
      assert.equal(metadata["local.checkpoint"].ready, false);
      assert.equal(metadata.unrelated, "keep");
      await commands.get("limits-reset").run();
      assert.equal(resets, 0, "declined confirmation cannot override guard");
      confirmed = true;
      await commands.get("limits-reset").run();
      assert.equal(resets, 1);
      assert.equal(prompts.length, 0, "manual resets use no LLM");
      await commands.get("checkpoint").run();
      assert.equal(
        prompts.length,
        1,
        "only explicit checkpoint preparation requests work from the model",
      );
      assert.match(prompts[0].text, /fix blocking findings, then review again/);
      assert.match(prompts[0].text, /Without Git/);
      assert.match(
        prompts[0].text,
        /this checkpoint request does not authorize one/,
      );
      assert.match(prompts[0].text, /leave reviewed changes uncommitted/);
      const beforeBurst = statusCalls;
      holdStatus = true;
      callback();
      for (let i = 0; i < 1000; i++) callback();
      connected();
      assert.equal(
        statusCalls,
        beforeBurst + 1,
        "only one status request in flight",
      );
      holdStatus = false;
      releaseStatus();
      await new Promise((resolve) => setImmediate(resolve));
      assert.equal(
        statusCalls,
        beforeBurst + 2,
        "one follow-up preserves changes during the request",
      );
      await new Promise((resolve) => setImmediate(resolve));
      assert.equal(
        statusCalls,
        beforeBurst + 2,
        "no idle retry loop after the burst",
      );
      const configBeforeBurst = configCalls;
      holdConfig = true;
      configUpdated();
      configValue = [];
      for (let i = 0; i < 1000; i++) configUpdated();
      assert.equal(configCalls, configBeforeBurst + 1);
      holdConfig = false;
      releaseConfig();
      await new Promise((resolve) => setImmediate(resolve));
      assert.equal(configCalls, configBeforeBurst + 2);
      assert.match(
        visibleText(slots[1].render()),
        /≋/,
        "one follow-up sees config changes during an in-flight read",
      );
      // Dispose with a read pending: its late response must not schedule a
      // queued reconnect follow-up or mutate the last rendered snapshot.
      const beforeDispose = statusCalls;
      const configBeforeDispose = configCalls;
      const lastText = visibleText(slots[1].render());
      holdStatus = true;
      holdConfig = true;
      configValue = [
        { type: "document", info: { compaction: { auto: false } } },
      ];
      callback();
      connected();
      configUpdated();
      cleanup();
      cleanup = undefined;
      statusValue = { available: false, active: 99 };
      holdStatus = false;
      holdConfig = false;
      releaseStatus();
      releaseConfig();
      await new Promise((resolve) => setImmediate(resolve));
      callback();
      connected();
      configUpdated();
      assert.equal(statusCalls, beforeDispose + 1);
      assert.equal(configCalls, configBeforeDispose + 1);
      assert.equal(visibleText(slots[1].render()), lastText);
      assert.equal(listeners.size, 0);
      assert.equal(stopped, 4);
      assert.equal(removed, 2);
    } finally {
      globalThis.setInterval = originalInterval;
      cleanup?.();
      loader.deregister();
    }
  },
);
