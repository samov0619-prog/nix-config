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
      const callback = () => listeners.get("rpc.local.limits.updated")?.({});
      const metadataCallback = (event) =>
        listeners.get("session.metadata.updated")?.(event);
      const connected = () => listeners.get("server.connected")?.({});
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
      const api = {
        client: {
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
              info: { muted: "blue-muted" },
              success: { muted: "green-muted" },
            },
          },
        },
        ui: {
          router: { current: () => ({ type: "session", sessionID: "ses_ui" }) },
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
      minuteClock();
      await new Promise((resolve) => setImmediate(resolve));
      assert.equal(
        statusCalls,
        1,
        "idle countdown does not poll the server/provider",
      );
      const pending = slots[1].render();
      assert.match(visibleText(pending), /Limits left: unavailable/);
      assert.match(JSON.stringify(pending), /Checkpoint/);
      assert.match(JSON.stringify(pending), /blue-muted/);
      assert.match(JSON.stringify(pending), /\+/);
      assert.doesNotMatch(JSON.stringify(pending), /⚠|\/checkpoint/);
      const beforeReconnect = statusCalls;
      // Simulate a transport gap: no updated/metadata event was delivered.
      // The native host stream reconnects without re-running plugin setup.
      statusValue = { available: false, active: 3 };
      metadata["local.checkpoint"] = { ready: true };
      assert.doesNotMatch(visibleText(slots[1].render()), /✓/);
      connected();
      await new Promise((resolve) => setImmediate(resolve));
      assert.equal(statusCalls, beforeReconnect + 1);
      assert.equal(
        metadataSyncs,
        1,
        "reconnect refreshes missed checkpoint state",
      );
      assert.match(visibleText(slots[1].render()), /Active: 3.*Checkpoint/);
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
        assert.match(sharing, /Limits: not exposed by token sharing/);
        assert.match(sharing, /Active: 2.*Checkpoint/);
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
        assert.match(text, /Limits left:/);
        assert.doesNotMatch(text, /token sharing/);
        assert.match(text, /5h .* · week /);
        assert.match(text, /Checkpoint/);
        assert.doesNotMatch(text, /wrap-up|stopping point|\/checkpoint/);
        for (const [label, mode] of [
          ["5h", primary],
          ["week", weekly],
        ]) {
          const group = nodes(rendered).find(
            (node) =>
              node.type === "span" &&
              node.children.some(
                (child) =>
                  typeof child === "string" && child.startsWith(`${label} `),
              ),
          );
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
      assert.match(switched, /Limits: not exposed by token sharing/);
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
      // Dispose with a read pending: its late response must not schedule a
      // queued reconnect follow-up or mutate the last rendered snapshot.
      const beforeDispose = statusCalls;
      const lastText = visibleText(slots[1].render());
      holdStatus = true;
      callback();
      connected();
      cleanup();
      cleanup = undefined;
      statusValue = { available: false, active: 99 };
      holdStatus = false;
      releaseStatus();
      await new Promise((resolve) => setImmediate(resolve));
      callback();
      connected();
      assert.equal(statusCalls, beforeDispose + 1);
      assert.equal(visibleText(slots[1].render()), lastText);
      assert.equal(listeners.size, 0);
      assert.equal(stopped, 3);
      assert.equal(removed, 2);
    } finally {
      globalThis.setInterval = originalInterval;
      cleanup?.();
      loader.deregister();
    }
  },
);
