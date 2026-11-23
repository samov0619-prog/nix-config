// Test-only observer of native rendered spans/cache; no production state patches.
import { Plugin } from "@opencode/plugin/tui";
import { readFileSync, renameSync, writeFileSync } from "node:fs";

export default Plugin.define({
  id: "test.personal-limits-probe",
  setup(api) {
    const base = process.env.XDG_STATE_HOME + "/personal-limits";
    let frame: { text: string; fg: number[] }[][] = [];
    const capture = (buffer: typeof api.renderer.currentRenderBuffer) => {
      frame = buffer
        .getSpanLines()
        .map((line) =>
          line.spans.map((span) => ({ text: span.text, fg: span.fg.toInts() })),
        );
    };
    api.renderer.addPostProcessFn(capture);
    let command = "";
    const timer = setInterval(() => {
      try {
        const next = readFileSync(base + ".route", "utf8").trim();
        if (next !== command) {
          command = next;
          api.ui.router.navigate(
            next === "home"
              ? { type: "home" }
              : { type: "session", sessionID: next },
          );
        }
      } catch {
        /* No requested navigation. */
      }
      const route = api.ui.router.current();
      writeFileSync(
        base + ".tmp",
        JSON.stringify({
          route,
          frame,
          muted: api.theme.text.muted.toInts(),
          info: api.theme.text.feedback.info.base.toInts(),
          messages:
            route.type === "session"
              ? api.data.session.message
                  .list(route.sessionID)
                  .map((message) => ({
                    id: message.id,
                    type: message.type,
                    status:
                      message.type === "compaction" ? message.status : null,
                  }))
              : [],
        }),
      );
      renameSync(base + ".tmp", base + ".state");
    }, 50);
    return () => {
      clearInterval(timer);
      api.renderer.removePostProcessFn(capture);
    };
  },
});
