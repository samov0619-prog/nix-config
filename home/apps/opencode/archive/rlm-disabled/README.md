# RLM — disabled experiment

This is a source archive, not an OpenCode configuration directory. Nothing here
is installed by Home Manager or loaded by OpenCode. Tests use `.ts.disabled` so
ordinary test discovery does not run them. The skill is not named `SKILL.md` and
is not registered. There is no runtime toggle.

The tool, recursive plugin, skill, usage writer and tests are retained together
for historical research. They depend on Zod, which is deliberately not vendored
or installed for this archive. To reproduce the experiment, copy it to a separate
temporary workspace, restore test filenames and provision dependencies there.
Do not re-enable it in the home profile as part of an ordinary test run.

Historical usage records under XDG state `opencode/task-usage` remain untouched.
The active, read-only `opencode-task-report` still understands them; its legacy
ledger tests verify report compatibility without loading any archived code.
