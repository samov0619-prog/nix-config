# OpenCode V2 verification and accounting

Pinned upstream: 2.1.4, `68bc26b7da1990ce10ffecfbc1e09eb13aa5d824`.
Historical model-quality experiments and V1 behavior are retained in
[archive/v1/BENCHMARK.md](archive/v1/BENCHMARK.md). They do not measure V2 quality.

## Reproducible checks

Run from the repository root. None activates a Nix generation:

```fish
node --test home/apps/opencode/tests/test_model_routing.mjs home/apps/opencode/tests/test_workspace_context.mjs home/apps/opencode/tests/test_git_offline.mjs home/apps/opencode/tests/test_voice_v2.mjs
node --test home/apps/opencode/tests/test_permission_stats_v2.mjs home/apps/opencode/tests/test_model_calls.mjs
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
```

The opt-in runtime test uses disposable HOME/XDG/config/data/state, a private
localhost server with synthetic credentials, and a localhost Responses mock.
It never attaches to the user's service/database/auth. MCP is disabled in the
synthetic Mac test. `--catalog` reads the bundled/native catalog, without calling
Big Pickle inference. No paid API calls are needed.

Coverage:
- Native schema, configured agents, server plugin discovery and activation.
- Native skill discovery parses both managed SKILL.md definitions and advertises
  their exact scoped descriptions alongside built-in opencode/report. The blanket
  discussion-map loading rule is absent. The HM-generation variant reads the
  actual deployed skill/rules symlinks. This validates installation and metadata,
  not the model's future choice to invoke a skill.
- Actual provider requests: Build High, title Luna Low, free main/child/auxiliary
  generation/compaction, live-root paid change for an already-created Explore
  child (Luna Max), Plan XHigh, compaction and summary High after Plan XHigh.
- Both summarizing compaction and native Responses streamed `compaction_trigger`
  checkpoints; both must finish with a stored `completed` compaction, not merely
  send a request. Provider error has no silent free→paid fallback.
- Root-only metadata mutation, foreign-key preservation, serialization/reopen,
  unrelated sessions, missing models/variants, cycles; local commands make no LLM call.
- Native TUI/SDK loading in a real PTY, `/switch-free` then `/switch-paid` with
  durable metadata and zero session messages, Unicode rename/workspace publication, Mac voice hotkey
  registration (platform guard on Linux); unit checks for voice cancellation,
  route changes, delayed transcription and no auto-submit.
- Home Manager's built model-routing directory is loaded through its real store
  symlinks; separate file symlinks break Bun's relative TS/JSON imports.
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
