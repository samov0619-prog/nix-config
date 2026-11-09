// Test-only observer: no settings mutations, prompt submission or model requests.
import { Plugin } from "@opencode/plugin/tui";
import { appendFileSync, writeFileSync, renameSync } from "node:fs";

export default Plugin.define({
  id: "test.theme-probe",
  setup(context) {
    const base = process.env.XDG_STATE_HOME + "/theme";
    const input = (sequence: string) => {
      if (/^\x1b(?:\[\?997;|\](?:10|11);)/.test(sequence)) {
        appendFileSync(base + ".jsonl", JSON.stringify({ sequence }) + "\n");
      }
      return false;
    };
    context.renderer.prependInputHandler(input);
    const timer = setInterval(() => {
      writeFileSync(base + ".tmp", JSON.stringify({
        rendererMode: context.renderer.themeMode,
        themeMode: context.themeMode,
        text: context.theme.text.base.toString(),
      }));
      renameSync(base + ".tmp", base + ".state");
    }, 50);
    return () => {
      clearInterval(timer);
      context.renderer.removeInputHandler(input);
    };
  },
});
