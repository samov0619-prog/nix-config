# OpenCode V2 verification and accounting

Pinned upstream: 2.1.4, `68bc26b7da1990ce10ffecfbc1e09eb13aa5d824`.
Historical model-quality experiments and V1 behavior are retained in
[archive/v1/BENCHMARK.md](archive/v1/BENCHMARK.md). They do not measure V2 quality.

## Latest review status (2026-11-02)

- All 59 Node unit tests passed, including production patch application and
  legacy-alias normalization with the `default` variant sentinel.
- The real picker/Free→Paid/Build→Plan PTY check passed with the installed binary
  and Home Manager generation. That binary predates the final legacy-alias fix.
- The attention PTY run passed window isolation, permissions, and todo review,
  feedback, cancellation, and a single commit, then failed with
  `Child completion attention not delivered`. Its cause remains unresolved;
  later assertions in that run were not reached.
- Runtime checks passed the catalog and main routing/todo paths before failing
  legacy-alias effort verification. The resulting compatibility fix is covered
  by unit tests, but its binary build was cancelled at the user's request.
  Runtime verification of that fix and a fresh native-compaction run are pending.

This is not a fully green verification matrix. Builds remain user-run by default;
resource-intensive runtime and PTY checks require separate approval. The commands
below document reproducibility, not authorization to execute them automatically.

## Reproducible checks

Run from the repository root. None activates a Nix generation:

```fish
node --test home/apps/opencode/tests/test_model_routing.mjs home/apps/opencode/tests/test_workspace_context.mjs home/apps/opencode/tests/test_git_offline.mjs home/apps/opencode/tests/test_voice_v2.mjs
node --test home/apps/opencode/tests/test_manual_model_routing.mjs
node --test home/apps/opencode/tests/test_model_variants.mjs
node --test home/apps/opencode/tests/test_permission_stats_v2.mjs home/apps/opencode/tests/test_model_calls.mjs
node --test home/apps/opencode/tests/test_skill_stats.mjs
node --test home/apps/opencode/tests/test_agent_todo.mjs
python3 home/apps/opencode/tests/test_skill_stats.py
node --test home/apps/opencode/tests/test_session_attention.mjs
python3 home/apps/opencode/tests/test_task_report.py
python3 home/apps/opencode/tests/test_silent_attention.py
python3 home/apps/opencode/tests/test_mac_audio_policy.py
nix build --no-link --print-out-paths path:.#packages.x86_64-linux.opencode
```

Using the binary returned by the build (Fish):

```fish
set binary /nix/store/REPLACE_WITH_BUILD_OUTPUT/bin/opencode
python3 home/apps/opencode/tests/test_v2_runtime.py $binary
python3 home/apps/opencode/tests/test_v2_runtime.py $binary --native
python3 home/apps/opencode/tests/test_v2_runtime.py $binary --catalog
python3 home/apps/opencode/tests/test_v2_runtime.py $binary --mac
python3 home/apps/opencode/tests/test_attention_tui.py $binary
env OPENCODE_TEST_BINARY=$binary python3 home/linux/modules/hyprland/tests/test_context_tui.py ContextTui.test_opencode_real_tui_plugin
# Also test the deployed Nix store layout (not just copied source files):
set generation (nix build --offline --no-link --print-out-paths path:.#homeConfigurations.samov-laptop.activationPackage)
env OPENCODE_TEST_BINARY=$binary OPENCODE_TEST_HM_GENERATION=$generation python3 home/linux/modules/hyprland/tests/test_context_tui.py ContextTui.test_opencode_real_tui_plugin
env OPENCODE_TEST_HM_GENERATION=$generation python3 home/apps/opencode/tests/test_v2_runtime.py $binary
env OPENCODE_TEST_HM_GENERATION=$generation python3 home/apps/opencode/tests/test_attention_tui.py $binary
# Fast targeted check of the HM-built urgency package without building every home package:
set urgency (nix build --no-link --print-out-paths --impure --expr '(builtins.getFlake ("path:" + builtins.toString ./.)).homeConfigurations.samov-laptop.config.xdg.configFile."opencode/plugins/quiet-urgency".source')
env OPENCODE_TEST_QUIET_URGENCY_PLUGIN=$urgency node --test home/apps/opencode/tests/test_session_attention.mjs
env OPENCODE_TEST_BINARY=$binary OPENCODE_TEST_QUIET_URGENCY_PLUGIN=$urgency python3 home/linux/modules/hyprland/tests/test_context_tui.py ContextTui.test_opencode_real_tui_plugin
```

The opt-in runtime test uses disposable HOME/XDG/config/data/state, a private
localhost server with synthetic credentials, and a localhost Responses mock.
It never attaches to the user's service/database/auth. MCP is disabled in the
synthetic Mac test. `--catalog` reads the bundled/native catalog, without calling
Big Pickle inference. No paid API calls are needed.

Coverage:

- Native schema, configured agents, server plugin discovery and activation.
- Native skill discovery parses all managed SKILL.md definitions and advertises
  their exact scoped descriptions alongside built-in opencode/report. The blanket
  discussion-map loading rule is absent. The HM-generation variant reads the
  actual deployed skill/rules symlinks. This validates installation and metadata,
  not the model's future choice to invoke a skill.
- Actual provider requests: Build High, title Luna Low, free main/child/auxiliary
  generation/compaction, live-root paid change for an already-created Explore
  child (Luna Max), Plan XHigh, compaction and summary High after Plan XHigh.
- Role-specific model aliases are absent from the real catalog; Sol exposes
  High/XHigh and Luna Low/Max on the real model IDs. The production patch stack
  is applied in unit fixtures; old persisted aliases resolve without database
  rewrites, including SessionInfo's `default` sentinel for a missing stored variant.
  The PTY checks effort through real Build/Plan switching (native Shift+Tab), not names
  such as `(plan)`; runtime mock requests check the actual wire effort.
- Both summarizing compaction and native Responses streamed `compaction_trigger`
  checkpoints; both must finish with a stored `completed` compaction, not merely
  send a request. Provider error has no silent free→paid fallback.
- Root-only metadata mutation, foreign-key preservation, serialization/reopen,
  unrelated sessions, missing models/variants, cycles; local commands make no LLM call.
- Manual model selection exits the live root policy in both modes, preserving
  unrelated and inherited child metadata. The actual patched selection functions
  cover lookup/write failure, retry, cycles, overlapping actions and route changes;
  automatic agent selection preserves routing. The picker awaits the selection
  before inspecting variants. The baseline metadata-only free→paid test passed
  while the public TUI model stayed free: V2 sync is cached hydration, not refresh.
  Both metadata mutations now invalidate before sync. The PTY probe checks the
  actual public model after each mode switch and after real picker selection,
  in addition to durable metadata and zero inference messages.
- Native TUI/SDK loading in a real PTY, `/switch-free` then `/switch-paid` with
  durable metadata and zero session messages, Unicode rename/workspace publication, Mac voice hotkey
  registration (platform guard on Linux); unit checks for voice cancellation,
  route changes, delayed transcription and no auto-submit.
- Home Manager's built model-routing directory is loaded through its real store
  symlinks; separate file symlinks break Bun's relative TS/JSON imports.
- Quiet urgency uses one self-contained store directory for its entrypoint, TS
  helper and Python kitten; HM-generation PTY checks those real neighboring files.
  The previous replaceVars output had no Nix references to its absolute source
  paths; the reported helper path was absent after GC. Todo was loaded during
  diagnosis, so this does not establish the same cause for its historical failure.
- Model-call journal matched one-to-one to all mock HTTP requests, including
  paid/free title, child errors, generation, both compaction modes and a real
  429→200 retry. Wire model/effort matched mock bodies; headers were correlated
  to attempts. Unit tests cover WebSocket response.create/control frames,
  disposal, bounded body inspection, private permissions and append failures.
  WebSocket transport has not been exercised against a real provider.
- Built HM server-plugin directory symlinks pass the realpath containment check
  in native discovery. The previous per-file index.ts symlinks were silently
  excluded; copied fixtures alone could not reveal this. Old leaf paths are
  replaced by new `*-v2` directory paths, keeping IDs/history unchanged.
- Attention isolation: the actual patched native notification source plus the
  local urgency plugin use one subtree predicate. Unit cases cover two clients,
  route changes, home/plugin routes, missing/cyclic ancestry, children, foreign
  lifecycle/errors/toasts/forms/permissions and existing native deduplication.
  `test_attention_tui.py` uses two real TUI processes/global tabs on one isolated
  authenticated server and a local mock provider. A test-only attention sink
  replaces audio/system notification delivery; Kitty attention escapes remain
  visible in each PTY. Live speaker/compositor delivery still needs target-host
  verification. The standalone Mac archive does not contain this binary patch.
- Git environment hook plus actual native shell parser/tool execution: saved
  Always cannot override policy denial, including compound commands and `git -C`;
  cached `remote show -n` remains allowed. Denied commands never execute, and
  the permitted cached command only examines a temporary local directory.
- Native permission events persist the correlated Always decision with mode 0600.
- Skill statistics use the native tool after hook and plugin KV storage. Unit
  checks cover session/assistant boundaries, later steering exclusion, repeated
  calls, concurrent duplicate callbacks/reload, unknown compacted queries,
  fail-open storage/lookup and no tool output/error persistence. The read-only
  report hides query text unless `--examples` is explicit. Runtime smoke exercises
  real successful/missing skill calls and verifies query/model attribution in KV.
- Read-only accounting against both synthetic schemas and a real V2 SQLite DB:
  exact mock token totals, compaction, descendants and merged V1/V2 recent sessions.
- Team/personal/project config documents and native env interpolation for Mac.
- Corporate Mac audio-policy regression: no home sound overrides/audio assets,
  replacement notification handler or home urgency plugin in the source overlay.

Unit plugin tests replace only `Plugin.define`, using public API-shaped fixtures;
they alone do not establish SDK compatibility. The native server and PTY smokes
exercise the real loader. Mac AVFoundation/Whisper, corporate endpoints, live
audio and compositor urgency require testing on the corresponding machine.
Legacy notification/mute sources and tests live under `archive/v1`, including
their V1 permission collector; they are not part of the current test glob.
Run them separately with `node --test home/apps/opencode/archive/v1/tests/test_*.mjs`.

## No global formatter

The Home Manager generation must not enable a global native formatter. The runtime
smoke verifies this configuration and checks that native write/edit/patch preserve
unformatted text without project formatting rules. Formatting CLI dependencies,
dispatcher scripts and the six-language autoformat smoke have been removed.
Repository-owned formatting rules are documented in the root `AGENTS.md`; they
do not enable native OpenCode formatting or reformat files during activation.

The 2026-10 project-config comparison used temporary inputs, without rewriting
repository files: Ruff 0.17.2 matched its isolated defaults on all 13 Python files;
Prettier 3.9.5 matched its defaults on 64 supported, non-ignored files; actual
LuaLS formatting with two-space LSP options matched the EditorConfig on 5 Lua files.
Beautysh 6.4.3 matched Neovim's `paronly` invocation on 6 shell files and a function
fixture. Both old and configured Beautysh fail on `hosts/server/preflight.sh` with
`indent/outdent mismatch`; no unrelated parser/style fix was attempted. The flake
formatter resolves to the exact installed nixfmt 1.3.1 binary used by nixd on PATH.

## Decision support / todo verification

`test_agent_todo.mjs` executes the real Markdown/Git implementation in disposable
`/tmp/opencode` repositories, with a fake native question executor. It covers:
lazy read/no initialization, approval/changed-note preview, English controls,
native dismissal-tag handling without swallowing unrelated errors, no truncation,
diff-looking note lines, decline/free-form revision,
stale content before/during confirmation, preserving staged/unstaged manual edits,
Plan denial, cancellation, native index locks, unrelated files, symlinks/size limits,
reload without implicit approval, deterministic priority/counters, same-user-turn
deduplication, duplicate IDs, and missing context attribution. Checkbox headings
and closed `<details>` blocks keep counters inside the spoiler, preserve manual
completion marks across confirmed revisits, and coexist with unchanged legacy layouts.
New structured notes receive sequential heading numbers, continuing after manual
gaps without renumbering existing headings. Numbers are independent of visits/IDs.
Review tests cover exactly one complete record per note, long lines/paths, Russian,
wide glyphs/emoji and literal HTML in code, with presentation wrappers removed.
One native form transports the entire batch and final decision. Proposal-bound consent,
missing/malformed/old Submit, stale edits, scoped ID/title/feedback, global feedback,
preserved drafts and renewed approval after wording changes are checked.
Navigation never writes or initializes Git; only final Submit without feedback commits
the batch once. Existing staged/unstaged changes stay intact.
Structured-delta tests exercise code-generated Markdown/spoilers, exact text replacements
scoped to stable IDs, byte-preserved unrelated/manual/legacy text, duplicate additions,
ambiguous fragments and embedded metadata rejection, and revisit-only proposals without
copying the file. `agent-todo-tui.tsx` uses public dialog/slot/keymap/form APIs;
`agent-todo-review.ts` is the shared versioned transport, not a separate database.
Left/right/Tab/Shift+Tab cycle, while text scrolls within each note tab.

The isolated `test_v2_runtime.py` also installs the actual plugin/decision-check
skill and uses the **real V2 Promise adapter and native question executor**. A
localhost mock provider calls todo tools; the test answers real forms through the
API, checks no/revise/yes behavior, commits in isolated HOME, and verifies the Plan
guard even with session-level edit allow. `OPENCODE_TEST_HM_GENERATION` checks the
real store-directory plugin installation too. No paid semantic inference is used.
The native adapter is also exercised across a multi-note batch, cancelling the
form and submitting its proposal-bound final decision with exactly one commit.
The batch supplies only new structured note wording; the saved file retains the original
prefix exactly. HTTP request counts stay constant throughout review: no extra model calls
for navigation, comparison, formatting or merging.

The resolver remains upstream. A separate reproduction showed that atomically
retargeting a plugin directory symlink in a running server can make todo disappear
without a failed inventory item, even after `/reload`: Bun's cached logical alias
resolves to the old entrypoint, which no longer passes containment. After HM updates
that change plugin store directories, finish active tasks and use
`opencode service restart`, then `opencode service status`; reopen TUI after binary
changes. Ordinary config edits still reload normally. Runtime smoke with
`OPENCODE_TEST_HM_GENERATION` verifies fresh-process loading of real store-directory
links, not live symlink retargeting in the same process.

`decision-check-scenarios.md` supplies behavioral fixtures for manual/model
evaluation, including negative cases. They are not an automated semantic classifier
test, and passing implementation tests does not establish model precision or helpfulness.
Live Kitty/F3/Neovim require target-host verification. Form controls are English,
including native free-form input; note text and model reasoning retain their language.

`test_attention_tui.py` additionally loads the actual todo plugin, reads a fresh
note and asks for confirmation through a mock model with the normal Build
permissions and only an explicit notes-read allow. It waits for the native form
API **and** English review options in real PTY output, declines and verifies that
neither the note nor Git is created. It then opens a second form and sends a real
Escape byte through the PTY: the form disappears, tool state becomes `completed`
with `declined` in both server history and TUI data cache, and the next prompt succeeds.
Baseline testing with the Location-patched binary and old plugin did not reproduce a
server hang: Escape produced a terminal `aborted` error and accepted another prompt.
Calling that persistent spinner intentional upstream behavior was not justified.
The todo-specific cancellation handler avoids that error/interrupt path; it needs no
additional binary patch. The binary without the Location patch creates the form but
does not display it: nested Promise-to-native question execution loses the
ambient Location. `question-location.patch` supplies the question plugin's own
Location for form/permission events. API-only reply tests cannot catch this bug.
The same test resizes a real client to **80×24**, reviews several notes including
a long Unicode/path-heavy note, and inspects actual rendered framebuffer cells on
each tab: note title, own-answer control and the familiar tab/scroll/confirm/dismiss
hint stay visible. End exposes the long note's unique final line; Home returns to
its summary. It sends real left/right/Tab/Shift+Tab, including cycling from Submit
to the first note; navigation keeps the same server form ID and request count.
It types/restores comments on two notes, checks their IDs and the retained draft,
and proves Submit with comments writes nothing. Escape, Reject and route changes
also write nothing; final Submit without feedback makes one batch commit. This catches
the oversized-description bug that API-only consent tests previously missed.
The real framebuffer also checks that structured `changes` is not flattened into
the generic tool summary behind the review; raw legacy-content history is unchanged.
The same pending review is checked at **140×40** and **160×48**, including the final
Submit tab: the native `Questions` composer must not show through and only one
own-answer control/confirmation hint may be visible. The opaque plugin backdrop
does not alter the host render tree or form cache. The previous presenter fails
this wide-terminal regression, even though its 80×24 tests pass.

## Accounting limits

`opencode-task-report` opens a SQLite read-only URI and a snapshot transaction.
It detects `session_v2`/`session_message`, preferring V2 for the requested session,
otherwise retains legacy `session`/`message`/`part` and saved ledger handling.
The report includes descendants, model routes, stored usage, cache, tool states,
saved retries and compaction markers; it does not expose prompts/source text.
It also reads per-session XDG state `opencode/model-calls/*.jsonl` (override with
`--calls-dir`) and lists transport attempts individually, separately from tokens.
Turn filtering uses attempt timestamps, including responses arriving after the
turn boundary; child attribution retains the existing start-time approximation.

Do not add ledger totals to DB totals when they describe the same requests.
The provider's token counters are not subscription quota. Session storage is
not an invoice: title, auxiliary generation and some failed/retried requests
may not be represented in durable session messages. Native V2 also stores title
usage events; this report does not add those to its message/ledger token totals.
The journal records HTTP dispatch hooks/response headers and experimental
WebSocket Open Responses response.create send hooks, not completed/billed calls.
It starts at installation, excludes calls outside session hooks and cannot prove
the final request after later hooks or server-side alias resolution. Oversized
HTTP JSON (>8 MiB) or unsupported bodies leave wire model/effort unknown. No
provider response bodies, URLs, headers, prompts or keys are persisted.
Report explicit coverage gaps rather than inventing missing usage.

The configured 212000 soft-input ceiling is not a proof of usable context or a
hard cap on individual request sizes. Checks happen between steps. Work High /
Plan XHigh and Explore Max remain hypotheses to compare on repeated frozen
real tasks, including children, corrections, cache and compaction.
