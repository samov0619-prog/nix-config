// Test-only sink: exercise the real notification plugin without audio/hardware.
// Every other TUI API (events, router, cache, plugin loader) is native.
import { Plugin } from "@opencode/plugin/tui";
import {
  appendFileSync,
  readFileSync,
  writeFileSync,
  renameSync,
} from "node:fs";
import { join } from "node:path";

export default Plugin.define({
  id: "test.attention-probe",
  setup(context) {
    // Test-only ways to exercise replacement/reload while a modal owns input.
    context.keymap.layer(() => ({
      mode: "modal",
      priority: 30,
      commands: [
        {
          bind: "ctrl+g",
          run: () => {
            void context.ui.dialog.alert({
              title: "Replacement dialog",
              message: "Todo must already be cancelled.",
            });
          },
        },
        {
          bind: "ctrl+y",
          run: () => context.keymap.dispatch("location.reload"),
        },
      ],
    }));
    const pane = process.env.KITTY_WINDOW_ID!;
    const base = join(process.env.XDG_STATE_HOME!, `attention-${pane}`);
    const original = context.attention.notify;
    context.attention.notify = async (request) => {
      appendFileSync(
        `${base}.jsonl`,
        JSON.stringify({
          type: "attention",
          sound: typeof request.sound === "object" ? request.sound.name : null,
          route: context.ui.router.current(),
        }) + "\n",
      );
      return { ok: true, notification: true, sound: true };
    };
    const events = [
      "session.execution.started",
      "session.execution.succeeded",
      "session.execution.failed",
      "session.execution.interrupted",
      "permission.asked",
    ] as const;
    const dispose = events.map((type) =>
      context.data.on(type, (event) => {
        appendFileSync(
          `${base}.jsonl`,
          JSON.stringify({
            type: "event",
            event: type,
            sessionID: event.data.sessionID,
          }) + "\n",
        );
      }),
    );
    let command = "";
    let frame: string[] = [];
    // Read only the buffer leased for post-processing, not a live native output
    // buffer from a timer (which can throw OutputBusy during presentation).
    const capture = (buffer: typeof context.renderer.currentRenderBuffer) => {
      frame = buffer
        .getSpanLines()
        .map((line) => line.spans.map((span) => span.text).join(""));
    };
    context.renderer.addPostProcessFn(capture);
    const timer = setInterval(() => {
      try {
        const next = readFileSync(`${base}.route`, "utf8").trim();
        if (next !== command) {
          command = next;
          context.ui.router.navigate(
            next === "home"
              ? { type: "home" }
              : { type: "session", sessionID: next },
          );
        }
      } catch {
        /* No requested navigation. */
      }
      const route = context.ui.router.current();
      const todo =
        route.type === "session"
          ? context.data.session.message
              .list(route.sessionID)
              .flatMap((message) =>
                message.type === "assistant"
                  ? message.content
                      .filter(
                        (part) =>
                          part.type === "tool" &&
                          part.name === "agent_todo_propose",
                      )
                      .map((part) => ({
                        id: part.id,
                        status: part.state.status,
                      }))
                  : [],
              )
          : [];
      writeFileSync(
        `${base}.state.tmp`,
        JSON.stringify({
          pid: process.pid,
          route,
          plugins: true,
          todo,
          frame,
        }),
      );
      renameSync(`${base}.state.tmp`, `${base}.state`);
    }, 50);
    return () => {
      clearInterval(timer);
      context.renderer.removePostProcessFn(capture);
      context.attention.notify = original;
      dispose.forEach((cleanup) => cleanup());
    };
  },
});
