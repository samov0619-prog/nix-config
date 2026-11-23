# OpenCode V2 verification and accounting

Current expressions and lock select the separate **upstream v2.4.0 flake**,
commit `44aed4fd144611879046ae923c25541f913780ad`. The user confirmed a successful
Linux HM build and the rebuild after the accounting fix; isolated target
runtime/PTY checks below now pass, including the refreshed report wrapper.
Real-backup copy migration and old-binary native reads of a fresh restore copy also
pass within the boundaries below. The user subsequently confirmed home HM
activation, `opencode v2.4.0+44aed4f`, and service start/status at
`http://127.0.0.1:13420` (2026-11-23), then working Free/Paid requests, correct theme
switching, retained history/attachments and MCP server connection. This is
user-reported live smoke acceptance, not all MCP tools, effort/quota/recovery
coverage. Installation restore and Mac remain separate stages; the agent did not
activate or modify live service/data.
See the [transition checklist](CONFIG-CHECKLIST.md#домашний-переход-на-upstream-flake-v240--план-небольшими-пакетами)
and [data/rollback procedure](UPGRADE-240.md).
Historical model-quality experiments and V1 behavior are retained in
[archive/v1/BENCHMARK.md](archive/v1/BENCHMARK.md). They do not measure V2 quality.

## Built Linux 2.4.0 isolated acceptance (2026-11-23)

Subsequent correction (2026-11-24): the user clarified that `/problem-brief` belongs
only to personal, at home and on the corporate Mac. The generator/HM/export now
register five personal commands and no Common brief. The historical four-command
runtime results below do not cover this relocation; no new live checks or builds
were run for it. All 21 focused source/evaluation tests pass (`test_problem_brief`,
`test_personal_layers`, `test_home_wiring`, `test_macos_export`); Python runtime
fixture syntax passes, but that fixture was not executed again. The user confirmed
Mac R3 application and the literal Common brief link target
`/Users/user/.config/opencode-local/commands/problem-brief.md`.
Incremental R4 rehearses exact R3 on that link-aware baseline, then passes
apply/check, whole-fixture corrected-tree comparison and reverse/check with exact
restoration. Both retained/removed `update-2026-11-16/` cases pass. Only seven
brief/documentation paths change; the only settings addition is personal
`commands.problem-brief`. Patch/hash are recorded in the Mac README; the user later
confirmed live R4 and the earlier README-only patch application. Runtime acceptance
remains unconfirmed.

Earlier documentation naming follow-up (2026-11-24): a four-guide-only patch over
R4 passed forward/reverse checks and full-fixture comparisons; all six export
tests passed again. The user applied it but rejected both the naming and the
loss of the original installation/resolve guidance. That patch is historical,
not the final documentation. Current titles use "Общая конфигурация OpenCode".
The original 208-line `trf.zip` README was read in full and its useful sections
restored with 2.4.0 corrections. Personal documentation now explains explicit
agents/commands registration, file resolution, discovery and native registry checks.
No config, prompt or policy changes, builds, activation or live acceptance.

Documentation restoration checks: all **22** focused source/evaluation tests pass
(`test_macos_export`, `test_personal_layers`, `test_home_wiring`, `test_problem_brief`),
including seven export contracts and the restored README sections/local links.
The static personal README keeps default-path examples plus explicit custom-XDG
guidance; custom-XDG assertions still cover every deployed runtime file.
The new two-README-only patch is based on user-confirmed R4 + the earlier README
patch. Forward/check, exact whole-tree/export comparison and reverse/check pass
both with and without historical `update-2026-11-16/`. Artifact, hash and application
instructions are retained in the repository's Mac README. No new runtime/mock
acceptance, builds, activation or live model/MCP checks were run.

Final documentation follow-up (2026-11-24): the user confirmed README-restore was
applied, then requested the original concise structure rather than expanded guides.
The six-README-only final patch restores useful original delegated-review guidance,
shortens Common/personal and task/browser guides, and leaves the problem-brief guide
and every runtime file unchanged. All 22 focused source/evaluation tests pass;
forward/reverse checks match the complete fixture and deployed export with/without
the historical folder, and all shipped guide links resolve. Patch/hash and user
application steps are in `macos/README.md`. No builds, activation, new mock
acceptance or live model/MCP checks.

### Real-backup working-copy migration (2026-11-23)

After separate approval, native built 2.4.0 migrated only a private DB/WAL/SHM copy
of `/home/samov/backups/opencode/261123tNov111795463834z`. The user reported the
stopped snapshot, checksum verification and SQLite integrity check on a disposable
copy. Agent rechecked the backup manifest and original DB hashes after acceptance.

**Pass:** 50 → 64 exact expected migration IDs; all 81 sessions and 11,809 messages
retained. All 18 retained non-journal tables match original-column row hashes,
including inline attachments, metadata, events and five untouched inbox rows.
The removed pending table was empty; new time_busy is NULL and part/blob/job/
automation/machine tables remain empty. Integrity is `ok`, foreign-key violations 0.
A second native open leaves logical data, schema and migration journal unchanged.

Native `serve --stdio` (not managed service) runs in user/mount/network/PID namespaces
with live HOME/runtime hidden and separate empty config/state/environment. No
restart lifecycle, copied config/registrations, API calls, models or MCP. Crucially,
the source copy has no schedule/automation tables; migrations create them empty,
so the always-started automation runner has no work or admission to recover.
Both startups exit cleanly on stdin EOF; syscall traces show no IPv4/IPv6 connects
or tool/MCP executables, only local nscd lookups. Provider use is additionally denied.

Full scope, source boundary and limitations: [UPGRADE-240.md](UPGRADE-240.md#снимок-и-миграция-рабочей-копии--2026-11-23).
Private temporary DB/probes/digests/logs: `/tmp/opencode/opencode-240-migration-872kpr8y/`.
This does **not** verify full installation restore, UI media, live models/MCP or Mac.
The immutable backup, live DB/service and HM generation were not modified.

### Fresh pre-upgrade restore and old-native reads (2026-11-23)

A separately approved fresh **full snapshot copy**, not the migrated DB, passes
file manifest hashes, all 27 literal symlink targets and their present Nix-store
availability, old generation 65 availability and ordinary-file `cli.json`.
Old binary **2.1.4+68bc26b** runs against its restored Data only, with separate empty
runtime config/state/cache, masked live HOME/runtime, no managed lifecycle,
project discovery/model fetch disabled and provider use denied. Restored original
config/plugins/MCP/registrations/PTY state are not activated.

**Native read pass:** 207 read-only GETs decode all 81 sessions / 11,809 messages
through real pagination. Session IDs/metadata/models/variants and message IDs/types/
order match SQLite expectations; active is 0 before/after. Payloads stay in memory,
with only a response digest saved. Clean EOF shutdown, empty stderr, no native
outbound IPv4/IPv6 connects or tool/MCP execs. Schema, 50 migration IDs, history,
inbox and all non-project table row hashes remain unchanged; integrity/FK pass.

**Strict whole-DB invariance did not pass:** two project rows gained only
`time_archived`. The old native archive sweep sees canonical directories as missing
because HOME is masked; both directories exist on the host. Source confirms this
startup sweep. All other project columns match. This observed isolation effect is
recorded, not suppressed by weakening the original assertion or adding a workaround.
It does not establish that full live restore is verified or that all startup
behavior is read-only.

Private inventory/digests/API result/trace and verification:
`/tmp/opencode/opencode-240-migration-872kpr8y/restore/`.
Backup manifest rechecked unchanged after the run. Full restored-environment
activation, UI/media/tabs and live model/MCP behavior remain untested; see
[UPGRADE-240.md](UPGRADE-240.md#изолированная-restore-репетиция--2026-11-23).

### Synthetic runtime and PTY checks

The user confirmed the retry of
`nix build /home/samov/nix-config#homeConfigurations.samov-laptop.activationPackage`
completed successfully. This covers that target's HM merge and realization at
build time, not Darwin or activation. The tested entrypoint is
`/home/samov/result/home-path/bin/opencode`, resolving to
`/nix/store/56hic3v2ayr9ki4a5cywia1w69v9bs7y-opencode-wrapped-2.4.0+44aed4f/bin/opencode`;
the binary reports **2.4.0+44aed4f**.

Completed checks use temporary private HOME/XDG/config/DB, explicit localhost
servers and mock model responses only. Project discovery/model fetching are
disabled; no credentials, live DB, managed service, MCP or browser are used.

| Check                                                                                                           | Result and boundary                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_personal_layers_runtime.py`                                                                               | All five generated-file cases pass: Common-only, home, corporate, home-no-todo and custom-XDG/store-like home-hm-layout. Native registration, `{file:...}`, role permissions/models, manual-only skill advertisement and Build/Plan-only todo context. Home/corporate additionally pass 48 native command invocations (four commands × three active roles × exact/empty arguments × two layers), retaining agent/model/low variant without children. Corporate native review/research inherit the parent model/variant without overrides and perform actual scripted policy/evidence reads; minimal Common, not real-model policy reasoning. |
| `test_v2_runtime.py`                                                                                            | Pass: paid/free/child/title/generate/textual-compaction routing and efforts, provider failure without paid fallback, retry, stored aliases, exact read-only accounting, Git-deny over saved Always, private permission/skill/call journals, todo native form transport/atomic fixture commits and Plan write denial.                                                                                                                                                                                                                                                                                                                         |
| `test_v2_runtime.py --native`                                                                                   | Pass: mock native streamed checkpoints retain the context provider/model/variant, including Plan XHigh rather than textual-summary High. This test-only setting does not enable native compaction in production.                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `test_v2_runtime.py --limits`                                                                                   | Pass: metadata-free prompts/tools and checkpoint ready/reset through actual native runtime hooks. This is not visual acceptance of every limits status/percentage.                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Default and `--limits` with `OPENCODE_TEST_HM_GENERATION=/home/samov/result`                                    | Both pass with the built plugin directories. Default additionally exercises native write/edit/patch without global formatting and verifies the disabled model-call logger stays absent. It uses fixture settings and the source reporting script, not a full installed-personal environment; the refreshed report wrapper is tested separately below.                                                                                                                                                                                                                                                                                        |
| `test_theme_mode_tui.py`                                                                                        | Both fresh-cache control and stale-cache regression pass in a real PTY, including repeated light/dark transitions and unchanged mutable CLI preferences.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `test_attention_tui.py` with that HM generation                                                                 | Full two-client PTY run passes using built todo/urgency plugins: ownership/background tabs, permission and child/parent completion isolation, owner transfer, home navigation, 140×40/160×48/80×24 todo rendering, scrolling/navigation/scoped feedback, Submit/Reject/Escape, route/replacement/reload cancellation, abrupt disconnect and reconnect. Native attention requests and Kitty escape sequences are observed; real audio/compositor behavior is not tested.                                                                                                                                                                      |
| `test_task_report.py` with `OPENCODE_TEST_REPORT_WRAPPER=/home/samov/result/home-path/bin/opencode-task-report` | All **13 tests pass**, including the actual installed wrapper against a private split-part DB: exact tool/error/token accounting, no raw output disclosure and byte-identical DB after reading. The wrapper's store script also matches the source byte-for-byte.                                                                                                                                                                                                                                                                                                                                                                            |
| `test_personal_limits_tui.py` with that HM generation                                                           | Home and corporate generated layers pass in native PTYs with the built limits closure. Real autocomplete/Tab selection/Enter loads manual `@discussion-map` into the stored user attachment and model request without a model skill-tool call. Rendered spans/colors verify idle auto muted, auto disabled absent, native running blue even with auto off, other-session isolation, completion clearing, re-enabled muted and home-footer muted; `Active: 0` and pending/ready handoff marks also render. No real quota identity, nonzero Active count, percentages/countdowns or real-model reasoning is tested.                            |
| `test_delegated_review_runtime.py`                                                                              | Both native background recovery cases pass with the actual generated home command layer. One 429 is absorbed by native retry with one child/invocation; eleven 429s exhaust ten native retries, deliver a terminal error report, then a real `sleep 20` precedes same-child continuation. Error → completed reports correlate to the same child; only one actual read occurs and its evidence survives. All 6/19 HTTP requests use the local `big-pickle` mock. Four cheap fixture unit tests also pass; this is not real-model recovery policy obedience or coverage of every budget/replacement path.                                      |

Initial legacy-fixture failures were investigated, not ignored. In 2.4, even
API-created child sessions report to and wake their parent
(`session/execution/subagent-report.ts`); fixtures now wait for that report and
parent execution before arming the next one-shot mock response. The accounting
expectation adds exactly three parent replies: ten samples × (20 input + 4 output)
= **240 processed tokens**, with two compactions. Attention checks wait for actual
tab/cache readiness and new lifecycle events, not a previous event for the same
session, and assert both child and resumed-parent notifications in the owner only.
No production attention/routing policy or timing delay was changed.

The recovery fixture was adapted to 2.4's always-background subagent contract:
both launch tool calls complete immediately; terminal failure arrives in a later
synthetic report. Its first target run passed the native-retry case and reached
successful same-child continuation, but read the final parent history too early.
`experimental.session.wait` waits for one agent-loop period, not all later report/
recovery periods. The fixture now waits for its final mock-provider reply before
native wait finishes that known period, without idle polling or a settling delay.
The corrected rerun passes both cases within the 240-second native-phase limit.
Terminal report → continuation is **20.107 seconds**; preserved reading is not
evidence of completed independent analysis. No production code or settings changed.
The focused source/command suite also passes **14 tests, zero skips/failures**;
both changed Python fixtures parse, and scoped whitespace/Prettier checks pass.
The full Node suite was not rerun for these test/documentation-only changes.

One actual compatibility fix was required: `scripts/task-report.py` previously
read only inline assistant content and omitted tool/text parts stored separately
by 2.4. It now follows native `SessionHistory.withParts`: ordinal `session_part`
rows first, then any inline tail; databases without that table remain supported.
The 13 accounting tests pass, including mixed split/inline ordering, exact
tokens, tools and output privacy. The full default runtime also checks **four
actual shell tool calls and three denials** in the read-only report. No blob bytes
are loaded or new raw source text included in reports.

After the fixture/report changes, the full Node suite was rerun: **256 pass,
zero skips/failures**. All four changed Python files pass AST parsing and scoped
diff whitespace checks pass. Changed TS/Markdown were formatted with the installed
Prettier 3.10.1; Ruff remains unavailable, so Python layout is preserved without
substituting another formatter. The backport inventory limitations below remain.

**Rebuild boundary closed:** the user confirmed the requested rebuild after the
reporting fix. The refreshed wrapper resolves to
`/nix/store/63p21j902pbvx3r33mgv50a3s17flaad-opencode-task-report/bin/opencode-task-report`
and executes `/nix/store/y365kpr5hdz12shknqhbri5s2qsf1icv-task-report.py`, which matches
the corrected source and passes the CLI fixture. The binary is unchanged. This
follow-up changes tests/docs only and does not require another runtime rebuild.
Builds remain user-run. Changes are uncommitted; no activation or live-service/data
mutation occurred. Fixture commits are only in disposable todo repositories under
temporary HOME, never the project or real notes.

Still unverified: real-model command/reviewer reasoning and policy obedience,
full recovery-budget exhaustion, later backoff steps, missing-ID/replacement paths,
real model/MCP/browser/voice/audio/
clipboard behavior, live quota percentages/countdowns/nonzero Active rendering,
full backup recoverability/installation restore, UI history/media, and live Mac
file types/integrations. Real-history copy migration is covered separately above.
Temporary passing logs are in `/tmp/opencode/opencode-240-compat-m8h7d_us/`
(`personal-240-runtime.log`, `v2-240-runtime.log`, `v2-240-native-runtime.log`,
`v2-240-limits-runtime.log`, `v2-240-installed-runtime.log`,
`v2-240-installed-limits-runtime.log`, `theme-240-pty.log`, `attention-240-pty.log`,
`personal-240-execution.log`, `personal-limits-240-pty.log`,
`delegated-recovery-240-rerun.log`; the first failed run is `delegated-recovery-240.log`).
The follow-up PTY frame/color snapshots are retained in the private directory
`/tmp/opencode/personal-limits-pty-svr6lsvq/{home,corporate}/snapshots.json`.
Passing recovery parent/child/request fixtures are retained privately under
`/tmp/opencode/delegated-review-runtime-u5bjjdd2/`.
This section is the durable evidence summary; `/tmp` is not deployment storage.

## Implemented upstream package, shared selection and Mac export (2026-11-23)

This section supersedes the **implementation status**, not the historical evidence,
of earlier research entries below. Both Linux/Darwin outputs now use upstream's
own nixpkgs `e21fec321d73511849707a7585e4ea155ee4bf40`, without new follows.
The separately approved lock update changed only OpenCode and its nested nixpkgs;
shared unstable did not change. Approved sequential bounded evaluations passed:
version **2.4.0+44aed4f**, Bun **1.4.4**, Node **24.22.2**, native env/hooks/completions
retained, Linux libstdc++/ALSA/PulseAudio added alongside native Wayland/PATH.
These are package metadata evaluations, not realization or library-loading tests.

U3 now puts canonicalization/live root policy/scoped overrides/role selection in
shared `select`; `resolve` retains model hooks and initialization. Preflight and
requests agree, including a session without stored agent using native default Plan.
Native compaction preserves the original provider/model identity; unavailable
textual routed summaries fail closed rather than silently switching providers.
Default background compaction, models/profiles and numerical buffer are unchanged.
All five production patches apply with `--fuzz=0` to the actual evaluated package
source `/nix/store/m6h2k5pxjj5bi5cihqa31bz1w6kwa8c1-source` (offsets permitted).

Durable tests: `test_nixpkgs_upgrade.mjs` has 13 passing patched-function/package
contracts; `test_upgrade_state.mjs` has five passing XDG/namespace/migration-journal/
message-source contracts. `test_upstream_package.mjs` adds three passing pin/output/
hook/wrapper fixture contracts. These use extracted source and effect/catalog/store
mocks, not full Effect, provider integration, typechecking or target binary execution.
U5 documents persisted routing/reset behavior, stopped-service backup and coordinated
binary/DB/config/state rollback. At that source-only stage real DB version, backup
completeness, migration on real history and restoration were untested. The later
working-copy migration above supersedes that migration status, not restore coverage.

`macos/export.nix` and `scripts/export-macos.py` produce ordinary staging files,
not a live installer. Protected fresh-`trf` settings/plugins/manifests/report and
five historical acceptance artifacts retain SHA-256 guards. Six export contracts
pass: neutral Common/seven MCPs, explicit personal registration/model inheritance,
custom-XDG paths, excluded mutable/private/voice state, manifest hashes and refusal
to overwrite/live-config destinations. The backup procedure is included in the
package. Old seed/R3 and Dasha EXAMPLE ONLY archives are untouched. Mac live path
types, post-snapshot changes, service env, MCP/browser/voice/CLI behavior remain open.

At that source-check stage no build/runtime acceptance had run; the later Linux
acceptance above supersedes that status. No activation, live service/data changes
or task commit. Historical 2.1.4 runtime and mocked limits rendering below are not
target 2.4.0 acceptance.

### Final source/unit checks and open repository blockers

All **256 Node tests pass, zero skips** across `tests/test_*.mjs`, with the actual
package source above and installed TypeScript parser explicitly supplied. This
includes the 21 upgrade/state/package contracts, six Mac-export contracts and all
existing routing, limits, todo, instruction, workflow and permission fixtures.
Two old HM test stubs needed the newly required todo/home/XDG inputs and `hasPrefix`;
their production assertions were retained. No real model/service was used.
The backport checker suite passes **24 synthetic tests**. Changed Python files
parse successfully; Ruff is unavailable. Pinned `nix fmt` and installed Prettier
3.10.1 were used on changed authored files, excluding preserved snapshots/archives.

Final Mac staging materialization contains **40 ordinary files**, including install
and backup/rollback instructions. Rebuild staging from repository sources before
transfer; `/tmp` is disposable, not the sole recovery copy or a deployment source.

The repository-wide inventory check is **blocked**, not passed: three existing
unregistered patches under `home/modules/kitty/macos/` (`kitty-keybindings-fix.patch`,
`kitty-keybindings.patch`, `kitty-ui.patch`) cause `Patch coverage mismatch`.
No Kitty files or inventory exceptions were changed to bypass that check, and no
reviewed fingerprints were acknowledged. The automatic update helper will still
stop at this inventory error until it is separately resolved.

`git diff --check` reports single-space blank unified-diff context lines in
`model-variants.patch` and `question-location.patch` (also patch EOF context).
The non-patch diff whitespace check passes. These context lines were not stripped
to silence Git: the full stack's no-fuzz application is the relevant patch check.

Reproduce the Node checks from this checkout (Fish; no build/runtime acceptance):

```fish
cd /home/samov/nix-config
begin
    set -lx OPENCODE_TEST_SOURCE (nix eval --offline --raw path:/home/samov/nix-config#packages.x86_64-linux.opencode.src)
    set -lx OPENCODE_TEST_TYPESCRIPT /home/samov/.local/share/nvim/mason/packages/typescript-language-server/node_modules/typescript/lib/typescript.js
    node --test home/apps/opencode/tests/test_*.mjs
end
python3 -B scripts/tests/test_backport_review.py
```

## User build: upstream node_modules hash correction (2026-11-23)

The first user-run Linux HM build failed in the fixed-output dependency, before
OpenCode's local patches/compilation. The actual derivation uses the pinned Bun
1.4.4, unpatched package source and native install/canonicalization scripts; no
local routing patch changes this dependency. Native `installPhase` completed, but
the tree hash was `sha256-sdMjb/l8SIthDbBJO3VzpyoOL9auoFGjVb6HdlxkQGg=` rather than
the tag's `sha256-1YrR3eb2bEvJZx3q3iIpcQHk36nULYu1gs3X6nBEj8o=`.

Merged upstream [PR #65824](https://github.com/anomalyco/opencode/pull/65824), commit
`7268011db4b9871f74403f4167c5f3f63d9fbb5f`, contains exactly this Linux replacement
and Darwin `sha256-3d3c6tnTD/fTefdrxUACkLLqKeXDDijLg2cp3yhz67Q=`. The PR reports a
successful x86_64-linux OpenCode build; ARM hashes come from the upstream bot run
linked in its description. This is upstream evidence, not our local Darwin build.
Both recursive Git trees were non-truncated: all 71 selected dependency inputs
(package manifests, bun.lock, bunfig/.npmrc, patches, node_modules recipe/scripts,
flake.nix/lock) have identical blob IDs between our tag and the hash-fix revision.
GitHub's three-dot compare uses a merge base and is not endpoint identity evidence;
the direct tree comparison supplies that check.

The minimal repair keeps the existing input/lock/source/toolchain and uses the
upstream `node_modules.override { hash = ...; }` argument inside the local package
override, for the two configured platforms only. No fakeHash, disabled hash check,
custom installer or Bun/lock update. Advancing the whole upstream input would also
change application code and expand acceptance scope unnecessarily. The temporary
override and its removal contract are registered as `opencode-node-modules-hashes`.
Package fixtures check both platform hashes and preserve the native recipe/hooks.

After this correction, sequential bounded evaluations of the actual Linux/Darwin
packages select their respective corrected hashes, retain the same dependency/main
source path and version, and confirm native `configurePhase` references the replaced
dependency. All 256 Node tests pass without skips; the checker suite passes 24 tests.
Scoped whitespace checks pass. These evaluations and fixtures do not build the
fixed-output dependency or confirm its reproducibility locally.

No retry build or activation was run by the agent. The first user attempt was a
**failed build**; the user subsequently confirmed the corrected Linux HM build
completed successfully. The built binary passed the isolated acceptance above.
This does not establish Darwin build success or repeated-build reproducibility.
Earlier source/unit success alone did not verify fixed-output hashes.

## 2.4.0 source preflight, not a retargeted package (2026-11-23)

Historical preflight, before the implemented package/selection changes above.

The user confirmed the corporate Mac already runs **2.4.0** and is considering
aligning home with it. Home repository patches still target the prepared 2.3.0
baseline; no lock, package or production patch was changed by this preflight.
Ten allowlisted source files from each upstream tag were downloaded over HTTPS
(not a Git checkout). Existing patches were probed on disposable copies only.

The 2.4.0 runner exports its existing `select` through `Service.of`. That new
context line rejects one hunk in session-routing and one in model-variants;
manual-model-routing then also fails because it depends on session-routing.
Question/attention patches apply unchanged. Updating only the two context hunks
in a scratch candidate allows the entire five-patch sequence with `--fuzz=0`
(some hunks have offsets). All six existing `test_nixpkgs_upgrade.mjs` contracts
then pass against 2.4.0: actual patched resolver logic with mocks, stored aliases,
compaction/question source contracts, native title helper and package-env/guard
fixtures. This is not typechecking, a build, full integration or real TUI acceptance.

One material upstream behavior change is confirmed in source and the
[V2 compaction guide](https://opencode.ai/v2/docs/compaction): background summary
preparation is now enabled by default. An unused summary can still cost tokens;
native compaction skips this path. The supported opt-out is
`compaction.background: false`; no such setting was added without agreement.
Direct use of the newly exposed `select` outside the patched resolver was not
covered by those six fixtures; the later U3 investigation below found a tool-policy
mismatch there. Plugin/CLI integration also needs target-version coverage before
home 2.4.0 can be declared compatible. The initial source comparison was
bounded to the ten selected files, not the entire release delta. A GitHub compare
query hit its 300-file cap and cannot establish absence of other affected callers.

Retained disposable evidence/candidate:
`/tmp/opencode/opencode-240-compat-m8h7d_us/`. This directory is not a durable
deliverable or an installation source. The findings and check limits above are
recorded independently of its retention. No builds/activation or task commit.

## 2.4.0 upstream toolchain source check (2026-11-23)

U2 in the [transition checklist](CONFIG-CHECKLIST.md#u2-зависимости-и-toolchain--linux-собран-darwin-только-evaluation)
records the independently read v2.4.0 lock, dependency/hash expressions and CLI
build helpers. Upstream pins nixpkgs `e21fec321d73511849707a7585e4ea155ee4bf40`:
Bun is 1.4.4, matching the root package manager, and default Node is 24.22.2.
Both target platforms have declared node_modules hashes; no fixed-output build
was run to verify them. The normal CLI build also builds/embeds the web app and
embeds the platform PTY asset. Package version includes a revision suffix.

The proposed local wrapper package set is upstream's own nixpkgs, without new
follows. No package/patch/lock implementation, Nix evaluation, build, target
runtime/PTY or live library-loading check was performed in this batch. Source
agreement is not proof of reproducibility, binary ABI compatibility or cache
availability; the checklist keeps those acceptance gaps open.

## 2.4.0 routing preflight mismatch reproduced (2026-11-23)

U3 in the [transition checklist](CONFIG-CHECKLIST.md#u3-публичный-select-и-routing--найден-функциональный-пробел-кандидата)
records the call paths and scenarios. A non-truncated GitHub tree for v2.4.0
commit `44aed4fd144611879046ae923c25541f913780ad` supplied all 537 code files
under `packages/core/src` (3,790,784 bytes). Static reference/import inspection
found one external direct `SessionRunnerModel.select` call, in SessionContext's
tool preflight. This bounded core scan is not the earlier capped release comparison
or a whole-repository/plugin audit.

Native `select` does not read our routing metadata; the candidate still applies
that policy only in `resolve`. SessionContext therefore can hide editing tools for
the durable model while the primary request uses another model. Actual native
modelTools chooses patch for GPT-5+ identities and edit/write otherwise. A Free
family's new general child can store its configured Sol model, receive a GPT tool
snapshot, then send its actual request through Big Pickle. TUI submission can
align a particular durable model, but is not a family-wide fix. Permissions remain
separate; no permission bypass or universal editing failure is claimed.

The scratch five-patch candidate again applies with no fuzz (offsets present).
Seven new source-fixtures pass: four reproduce mismatches, one checks role/effort/
override/live-root request routing, one is an aligned-model control and one checks
raw-select versus patched-resolve handling of a legacy alias. They execute actual
select/resolve/modelTools functions with mocked generator effects/catalog/store/
hooks, not full Effect, SessionContext, tool execution, a model or TUI. Passing
reproduction tests do not mean the defect is fixed. The old six upgrade fixtures
were not rerun in this batch, and their earlier success did not cover this path.

Candidate acceptance now requires a functional selection-policy adaptation plus
regression coverage, not only the two context adjustments. No production package,
patch or lock was edited, and no build or target-runtime/PTY was run. Disposable
inventory, patch log and reproduction script are under
`/tmp/opencode/opencode-240-compat-m8h7d_us/u3/`; the durable findings and limitations
are in the checklist and this section.

## 2.4.0 compaction policy source check (2026-11-23)

U4 in the [transition checklist](CONFIG-CHECKLIST.md#u4-compaction-и-стоимость--source-пути-проверены-background-оставляем)
compares the V2 compaction guide, v2.4.0 core source, our candidate and prepared
home settings. Ordinary/background summaries share selectModel and the compaction
role. Paid selects Sol high; Free selects Big Pickle; no profile/explicit agent
model preserves the session model identity. Root routing metadata takes precedence
over agents.compaction.model, and summary is a separate session-generate policy.

The configured Sol/Luna input cap is 244k despite the 1.05M context value; with our
32k buffer the primary ceiling is 212k. Smaller summary windows can force lossy
transcript shortening. Output budgeting is not a universal hard cap: the native
OpenAI hook removes maxTokens. Template/finish checks do not prove semantic quality.
Prompt-cache eligibility is not a measured hit or a cross-model guarantee. Held
text summaries can survive model/profile changes, and background=false is not a
cancellation API for existing work. No cost/quality/cache experiment was run.

The local patch also removes upstream's unresolved-agent-model fallback and may
reroute native compaction away from its original session model. Native is not
enabled by the prepared settings; the latter is a conditional source-contract
gap, not a demonstrated live failure or an established new 2.4.0 regression.

Final ten source-fixtures pass after correcting initial harness extraction errors.
They execute actual budget/TTL/history-selection/helper/hook code with mocks;
model resolution uses the repository routing helper, not full Effect/provider
integration. Some fixtures demonstrate patch incompatibilities, not their repair.
Script: `/tmp/opencode/opencode-240-compat-m8h7d_us/u4/test-compaction-policy.mjs`.
Only documentation and disposable research artifacts changed. No production
settings/package/patch/lock, build, real model calls, activation or task commit.
The user subsequently chose to retain default background compaction and observe
actual usage before considering an opt-out. No background=false setting is added;
any cheaper-model experiment remains a separate decision.

## Compact limits display and auto-compaction indicator (2026-11-23)

The limits TUI drops the `Limits left`/`Limits`, `Checkpoint` and weekly `week`
labels while preserving both percentages/reset countdowns, independent warning
markers, active-worker count and the blue `+` / green `✓` handoff status.
One muted `≋` means configured automatic compaction is enabled; the same icon is
blue while the current session is compacting, including manual compaction with
auto disabled. Otherwise disabled or unreadable configuration hides that icon.
It does not indicate a running or held background preparation.

The existing TUI plugin uses native `client.config.get({ location })`, initially,
on `config.updated` and after reconnect. The v2.4.0 generated client/types and
server config handler were checked at commit `44aed4fd144611879046ae923c25541f913780ad`:
the response is ordered Config.Entry documents/directories, not a merged object.
The indicator folds only explicit auto values in priority order, retaining the
native true default; a later background/buffer setting cannot erase auto=false.
Reads coalesce with one follow-up and are ignored after disposal. No idle config
polling, server-plugin change, new binary patch, dependency or model call is added.

The activity extension reads the latest compaction message through public
`data.session.message.list`, not a second start/end map. The same v2.4.0 revision's
`packages/client/src/solid/data.ts` projects compaction started/ended/failed events
into running/completed/failed messages. Current-session messages are invalidated
and synced after reconnect; ordinary rendering/tab changes read the reactive
host cache. Background precompute in core emits no matching lifecycle pair, so
the plugin makes no attempt to infer its activity/readiness.

All **19 limits/TUI tests passed**, without skips, using the installed TypeScript
parser for the existing TSX public-API fixture. Coverage includes both slots,
default/layered/disabled/error config, background independent from auto, live
config events, reconnect, burst coalescing, disposal, native projected activity
states, session/home routing, manual compaction with auto disabled, and the
existing per-window warnings/manual checkpoint behavior.
This is mocked rendering/transpilation, not native event-to-cache integration,
full typechecking, real Solid/OpenTUI/PTY, glyph/font or target-binary acceptance.
Formatting uses installed Prettier 3.10.1 with project configuration. No build,
activation, package/lock change or task commit; the home migration remains pending.

## Neutral instruction core and declarative home wiring (2026-11-23)

`AGENTS.common.md` contains environment-neutral engineering/evidence, formatting,
verification and artifact rules, without Samov's roles/routing, Goals or Fish.
`instructions.nix` exposes homeBase/homePersonal, their combined regression view
home, and corporate/corporatePersonal. Corporate Git/requirements/task-log contracts
are preserved; the old automatic discussion-map rule is intentionally removed.
The original home 68-bullet/hash guard passes after narrowly reversing only the
documented path/delegation migrations, with separate comment guidance coverage.

`default.nix` now installs only homeBase globally, retains all provider/safety/
compaction settings through `v2-base-settings.nix`, and installs generated personal
files plus `home.sessionVariables.OPENCODE_CONFIG`. Old global personal command/
policy/skill declarations are removed. Home role models remain unchanged in the
personal JSONC. Todo permissions live there too; `todo.nix` installs one coherent
four-file directory at `opencode-local/plugins/agent-todo`, not escaping file links.
Paths use actual `xdg.configHome` and home directory.

127 focused Node tests pass. Actual-module composition tests cover Linux/Darwin,
custom XDG, both todo states, old-entrypoint absence and base/model preservation.
They use lazy/stubbed package constructors, not the full pinned HM module merge.
Installed `opencode v2.1.4+68bc26b` passes five generated-files runtime cases:
Common-only, home, corporate, home-no-todo and custom-XDG home-hm-layout. The last
uses a store-like directory link; it does not realize a Nix derivation. Local
mock requests include actual new base/personal instruction texts and confirm
todo context only for Build/Plan and no manual-skill advertisement. Registries
confirm command bodies/metadata, systems/permissions/models and active plugin IDs.
Settings remain a minimal fixture, not full Common/seven-MCP corporate integration.

Python AST and layer-file whitespace checks pass. Broader `git diff --check` still
reports pre-existing whitespace in model-variants/question-location patch files;
those lines were not changed by this layer batch. Full-runtime fixture consumers
now select the personal todo/skill paths and manual-only skill metadata; skill-tool
accounting uses auto-invoked git-regression-rollback, not manual discussion-map.
These fixture edits passed syntax checks only; full runtime/PTY was not rerun.
Changed Nix files were formatted
with pinned `nix fmt --offline --no-write-lock-file`; `flake.lock` is unchanged.
Prettier/Ruff are unavailable. Full pinned-HM evaluation, builds, full runtime/PTY,
2.3.0 runtime, live Mac, command execution/arguments, delegated inheritance/review,
manual skill/TUI, new todo TUI placement, real-model intent recognition and browser
acceptance remain pending. No activation, note writes, real model/MCP/browser,
live service mutation or task commit. See `PERSONAL-LAYER.md` for acceptance order.

## Earlier generated personal-layer source package (2026-11-23)

`config/personal-layers.nix` defines home/corporate settings and file records for
native `OPENCODE_CONFIG` loading. Metadata lives in JSONC; asserted fixed headers
are removed from the four command sources before `{file:...}` interpolation.
Home retains all role models/systems/permissions; corporate review/research have
no model overrides. Policies remain files in the personal directory, problem-brief
stayed common in this historical package (corrected to personal on 2026-11-24),
discussion-map is manual-only, and only home contains the explicit
relative todo plugin and its four-file server/TUI source closure. No CLI, voice,
provider or MCP configuration is copied into the overlay.

87 focused Node tests pass, including seven new pure source/evaluation contracts.
`test_personal_layers_runtime.py` materializes actual generator `.files` without
rewriting generated JSONC. Installed `opencode v2.1.4+68bc26b` passes four private
server cases from an unrelated CWD: Common-only, home, corporate and home without
todo. There are no discovery symlinks. Native registries/config documents confirm
command bodies/metadata, role systems/denials/home model references and manual
skill path/autoinvoke state. The relative plugin loads as active `local.agent-todo`;
the actual shared `local.git-offline` plugin stays active in all four cases.

Local mock-provider requests confirm personal instruction loading, no manual-skill
advertisement and note tools/full guidance only for Build/Plan. Explicit session
model selection keeps all requests local without changing generated role settings;
it does not test delegated model inheritance. Common-only ignores adjacent personal
definitions. The Common base is a minimal neutral fixture, not the complete final
Common or seven-MCP corporate setup. Reviewer policies are checked as packaged
files/systems, not by executing the delegated workflow. No note tool or command
ran. No real model/MCP/browser, user data, live service mutation or activation.

At that source-only stage, instruction neutralization, Common/HM wiring and
old-discovery removal were still pending; the later batch above supersedes this
status, not the historical test evidence. No 2.3.0 binary, live Mac, command arguments/execution, TUI/manual invocation,
real-model todo selection or browser acceptance. Python syntax/changed-file whitespace
checks pass; Prettier/Ruff are unavailable. No build, installation, lock change or
task commit. See `PERSONAL-LAYER.md` for scope and the remaining acceptance order.

## Decision Support archived; todo scoped to Build/Plan (2026-11-23)

The user requested archiving Decision Support/decision-check while preserving the
ordinary natural-language "add to todo" workflow. The old combined module,
instruction, skill (including the Russian quotation) and manual scenarios moved
byte-for-byte into `archive/decision-support/`; SHA-256 guards verify preservation.
They are no longer installed. `todo.nix` is the independent home opt-in via
`programs.opencode.todo.enable`; the removed combined option reports migration
guidance instead of silently changing an old override's meaning.

`config/todo-settings.nix` denies both custom tool actions by default and allows
them only for Build/Plan, without granting edits. Full note guidance is attached
to the existing proposal tool through `agent-todo-instructions.ts`, not a global
instruction or new skill/hook. Native consent, store/Git implementation and Plan's
edit guard are unchanged. No unsolicited task creation or automatic idea saving was
added. This scopes model context/tools, not arbitrary filesystem access.

80 focused Node checks pass: todo store/consent/Plan/manual edits, module/archival
contracts, instruction layers, Git approvals/offline, review requirements and the
two command sources. A new focused isolated runtime fixture passes on installed
`opencode v2.1.4+68bc26b`: actual local mock-provider requests include note tools
and their guidance for Build/Plan and omit them for general/explore/research/review.
Decision Support instructions and decision-check are absent. No todo tool ran,
no notes were written and no real model/MCP or live service was used. The private
server stopped and its disposable data were cleaned. This does not establish
real-model intent recognition or native browser/TUI behavior on the new generation.

Python syntax passes for the focused runtime, full runtime and attention PTY
fixtures; their dependency copying now includes the note-guidance module. Full
runtime/PTY and the pinned-HM config-target evaluation were not rerun. The latter
now selects the independent todo option rather than the archived combined one.
Nix files were formatted with pinned `nix fmt`; its incidental lock-file pruning
was restored exactly, leaving `flake.lock` unchanged. Prettier/Ruff are unavailable.
No project build, activation, remote Git operation or task commit was performed.

## nixpkgs-unstable transition preparation (2026-11-22)

The dedicated OpenCode input was removed from flake wiring; both Linux and HM
Darwin packages now wrap `nixpkgs-unstable.opencode`. Build channel `prod` is kept
through the native build environment (nixpkgs defaults to `latest`), preserving
the existing TUI storage and service namespace. The lock is intentionally
unchanged until the user's update. An explicit >=2.3.0 guard rejects the currently
locked 2.2.5 before applying incompatible patches. The independent corporate Mac
distribution and existing uncommitted instruction-layer work remain unchanged.

Five local patches apply to selected pristine v2.3.0 files with GNU patch,
`--fuzz=0`. Backend routing now uses native request kind/agent, preserving title,
compaction and summary routing before the new native same-provider model hook.
Canonical aliases, manual model/effort policy and explicit Question Location stay.
Notification patching retains native direct-child completion and both quota-error
exclusions. The original theme-cache patch remains as a reference but is no longer
applied: 2.3.0 contains the exact priority expression. Its source-policy controls
now execute the native block; native PTY acceptance is still pending.

34 focused Node source/fixture checks pass, including six new upgrade contracts:
actual backend resolver routing with request kinds/live-root metadata, stored alias
compatibility, compaction/question source guards and native terminal-title cleanup
for the reported tab-containing title, plus actual local Nix override evaluation
for channel/env preservation and rejection of 2.2.5. Attention coverage also checks native child
completion and free/go-limit suppression. Another 62 plugin/config/instruction
fixture checks pass; one limits TSX fixture is skipped because TypeScript is not
installed. Fixtures do not establish real plugin discovery/API compatibility,
native OpenTUI operation, complete TypeScript checking or model behavior.

Read-only package evaluation with the old lock fails with the intended update
instruction. The backport inventory command is blocked by existing unregistered
Kitty Mac patches outside this task, before reaching the selected OpenCode entries;
no unrelated registry entries or accepted fingerprints were changed.

Changed Nix files were formatted with the project's pinned `nix fmt`; Prettier
is unavailable, so Markdown/JSON/JS formatting was not run and no replacement
formatter was installed. Non-patch whitespace checks pass; blank context lines
inside unified patches remain intact as patch syntax.

No OpenCode/HM build, new-binary runtime/PTY, activation, service mutation or commit.
Full merged HM evaluation after the user's input update is pending. Follow the
ordered update/build/isolated-test/backup/activation procedure in README.md. Older
entries below describe 2.1.4 (`68bc26b7da1990ce10ffecfbc1e09eb13aa5d824`), unless
they explicitly identify another version, and are not new-version acceptance.

## Corporate tracker instructions and overlay registration (2026-11-23)

Future corporate instruction sources now select XTracker for current tasks and
optional task-log keys. Samov's personal Mac rules require confirmed `FBDC-<number>`
keys for new branches/commits; older Git history controls only the remaining style.
The corporate-only `skills/task-summary-log/SKILL.md` source uses full keys, checks
legacy filenames/task identity before creating a log and updates existing logs in
place without automatic renames. It is not installed by HM. The fresh archive,
historical seed/R3, MCP configuration, permissions and git-offline are unchanged.

29 focused Node checks pass: instruction layers, Git approvals/offline policy and
review requirements. The layer guard now allows only the two specified tracker
text replacements relative to R3 rather than requiring obsolete byte equality;
the rest of the team file remains byte-identical. New guards cover personal key
precedence, log migration and absence of corporate rules/skills in HM output.
Prettier is unavailable; no replacement formatter installed. No build or activation.

In the same task, a disposable isolated registration fixture passed on installed
`opencode v2.1.4+68bc26b`, using private servers/HOME/XDG and an unrelated CWD.
Common plus explicit personal `OPENCODE_CONFIG` resolved relative `{file:...}`
bodies and registered four personal commands and a reviewer with its metadata and
denials, without symlinks. Common-only omitted those personal entries. The registry
required a bounded readiness wait; both servers were stopped. Existing delegated
review command bodies were real, but the new procedures and reviewer system were
markers. No session, model/MCP call or command execution occurred. This is not
argument-expansion, model preservation, delegation/browser, 2.3.0 or live Mac
acceptance. Both new personal procedures are agreed as commands, not skills; the
broader layer split is still pending. Details and scratch
fixture location are recorded in CONFIG-CHECKLIST.md.

Follow-up: the two English command sources and separate short Russian guides
`task-analysis.README.md` and `browser-verification.README.md` are now prepared.
Six source-contract tests pass for
current-session metadata, read-only analysis, API/deployment distinctions, live
versus passive browser scope, shared-browser safety and evidence/coverage limits.
The isolated 2.1.4 registration fixture was rerun successfully with the actual
bodies and descriptions of both new commands instead of markers. The reviewer
system remains a fixture marker. No command execution or model/MCP calls occurred;
neither HM wiring nor a real personal overlay was changed. Runtime behavior,
arguments, agent/model preservation and browser acceptance remain untested.
The combined focused suite passes all 35 checks. Whitespace/fence checks pass;
Prettier remains unavailable. No commit, build, activation or live service mutation.

## Instruction layers: HM versus standalone corporate (2026-11-19)

`config/instructions.nix` explicitly composes three outputs: common personal +
home for HM on either platform; pure corporate team policy; common personal +
corporate-personal routing for the independent port. HM uses native
`xdg.configFile.text`, not an extra loader/hook or an OS-based export switch.
Nix/nsh, local checkout, scratch directories and home review paths stay home-only;
corporate task sources/MCP/tickets/logs stay out of HM. Generic comment guidance
previously in corporate personal is now shared. Decision-support/todo remains
separately home-only, including in the updated source runtime fixture.

58 lightweight Node checks pass across instruction layers, goal/approach,
delegated review/Chrome, Git approvals, requirements and optional-logger wiring.
The new seven layer checks evaluate the actual composition, test both module
platform branches without realization, enforce negative cross-contamination
guards, preserve the 68 pre-split home bullets by count/hash and compare the pure
corporate file byte-for-byte with the R3 team baseline. They also preserve the
corporate personal review/comment sections. An obsolete `.source`-shape assertion
was updated to the requested merged `.text` wiring; behavioral guards remain.
These are source/evaluation fixtures, not complete merged HM evaluation, native
OpenCode instruction discovery, model compliance or live corporate Mac acceptance.

The source runtime fixture now uses the composed variants and no longer injects
home decision-support/todo into Mac mode. Its Python syntax passes; the full
runtime/PTY check was not run. Nix files were formatted through pinned `nix fmt`
(nixfmt 1.5.0). Prettier/Ruff remain unavailable; no substitutes installed.
No build, activation, service restart, commit, new Mac patch or live Mac mutation.
Historical seed/R3 policy bytes and the released patch remain unchanged; future
exports use the allowlisted outputs documented in the Mac guide.

## Acceptance status (2026-11-17)

`not-verified-in-wilde` — saved at the user's request before live acceptance.
The requirements-source, review-reasoning and simpler-approach changes have local
source/fixture coverage, not acceptance of actual model behavior. R3 Mac native
discovery and corporate MCP behavior remain unverified; applying R2 is not that
acceptance. Keep this marker until the relevant live scenarios are checked and
their results recorded. A commit does not change this verification status.

## Mac patch R3: source-only team rule, personal workflows (2026-11-16)

The user reports R2 applied and rejects its ownership boundary: team AGENTS must
select requirements sources without personal reviewer/command dependencies.
R3 is incremental **after R2**, not a cumulative replacement or an instruction to
reverse R2. Artifact: `~/Downloads/opencode-mac-update-2026-11-16-r3.patch`.
SHA256: `4aefdc1f0887a91c6391dc53b7ff1da7afde9e676fe19cb8cd77d0c6de833fa0`.

Team AGENTS retains only the independent `Requirements Sources` addition; its
remaining original bytes match the input baseline. Personal ordinary/delegated
review and passive Chrome routing move to the already-loaded personal AGENTS.
Reviewer and code-review template read policy directly from `opencode-local`.
R3 deletes the two team policy symlinks, retaining their actual personal files and
all three existing native command/agent discovery links. No JSON/routing/model or
permission changes. Goals and Approach is byte-identical to R2; home runtime
configuration remains unchanged. The Mac command differs from the shared template
only by policy location, with a parity guard to prevent accidental workflow drift.

52 lightweight Node checks pass, including two new layering/path-parity guards;
existing goal/baseline/link guards now enforce the corrected ownership contract.
HM evaluation performs no realization and emits only the existing quota warning.
The actual native patch changes ten paths (eight regular files, two symlink
deletions). A selected-file fixture reconstructs ZIP content + three live links +
applied R2. R3 preflight/apply succeeds, all target bytes match, both team policy
links disappear and personal policies remain byte-identical. Three discovery-link
strings/inodes and seven private/unrelated sentinels are preserved. Exact reverse
returns R2. Duplicate application, a conflicting target and the pre-R2 state are
rejected; a conflicting direct apply writes nothing. Team has no private file or
command dependency, while personal consumers name local policy paths. These are
source/fixture checks, not model compliance or live Mac discovery/MCP acceptance.
Prettier remains unavailable; no substitute installed. No build, activation,
restart, live config edit, Git index/history change or commit. R2 is retained as
the applied baseline artifact; only disposable R3 work files are cleaned.

## Mac patch R2: preserve installed links (2026-11-16; user reports applied)

The user's Mac preflight rejected R1 with `wrong type` for the team reviewer and
two review commands. No apply occurred. Treating flattened ZIP types as live types
was a delivery error; R2 does not remove or recreate those three paths. It updates
their regular-file targets in `opencode-local` and creates only the two new policy
symlinks. The existing links' actual destinations must be checked separately with
the documented `readlink` preflight: Git cannot validate paths excluded from diff.

Applied baseline artifact: `~/Downloads/opencode-mac-update-2026-11-16-r2.patch`.
SHA256: `093cc0e44fc527c472980063270b8a3d6937a0c98f2b9ee55024bab2b1f981b3`.
It changes 16 paths (14 regular targets, two new symlinks), with no changes to the
three existing links or config/provider/MCP/plugin/audio/auth/Git data. On a Linux
fixture with three existing relative symlinks, R1 reproduces all three reported
errors; R2 preflight/apply succeeds. Exact target bytes, preserved link strings and
inodes, both new link resolutions and seven untouched sentinels pass. Reverse
restores the exact initial file/link state; reapply and a conflicting targeted file
are rejected without partial writes. Source bytes and input ZIP remain stable.
The obsolete R1 artifact and task scratch were removed after verification. No live
Mac config change, Mac runtime/model/MCP check, build, activation or commit occurred.

## Goals/approach and superseded R1 Mac patch (2026-11-16)

The home global AGENTS and corporate **personal** AGENTS now share a bounded
goal/approach check before materially increasing complexity or scope. It surfaces
a simpler viable alternative without vetoing learning/experimentation, requiring
routine confirmation or repeatedly challenging an informed choice. Operational
permissions/project constraints remain applicable. No plugin, hook, dependency,
new instruction-loading mechanism or decision-support opt-in was introduced.
The corporate team AGENTS still changes only its review/requirements section;
both team and personal rules preserve the exact input baseline outside additions.

`~/Downloads/opencode-mac-update-2026-11-16.patch` is a native Git patch against
the unchanged `trf.zip`, not a replacement configuration or update to the old seed.
SHA256: `f187bdbc4bdadaad1236a64129ff5423e33b6b4a31fad0bf3729b7f0188fff55`.
It updates 19 unique paths: 14 regular-file targets and five team-to-personal
symlinks encoded with native mode `120000`. Four personal source links are
materialized as file content. The install guide and the 14 requirements-source /
six approach scenarios are placed under `opencode-local/update-2026-11-16/`.
No JSON/CLI/provider/MCP settings, credentials, plugins/audio, Git metadata or
session history change; problem-brief already matches. Application from the common
config parent uses `git apply --check` then `git apply`, without index/staging,
commits, a script, extraction or manual symlink repair. The mistakenly prepared
tar.gz was removed after the patch passed. Sources/instructions: `macos/trf-review/`.

50 lightweight Node checks pass (the previous 47 plus three new text/parity/baseline
guards), along with both Mac audio-policy checks. HM evaluation performs no
realization and reports only the existing quota-source warning. These checks
predate the delivery-format correction; the underlying policy/command/role bytes
are unchanged. The generated native patch passed path allowlist/full-index/mode
checks and actual Linux `git apply --check`, apply and reverse. All target bytes,
types and five internal symlink resolutions match; seven unrelated config/CLI/env/
Git/plugin/problem-brief sentinels remain unchanged. Reverse restores exact initial
file bytes/types/modes. Reapplication is rejected. A deliberately conflicting
baseline rejects even direct apply without partial writes; an already-restored
symlink layout is explicitly rejected as a different baseline, without writes.
This patch does not silently normalize arbitrary live layouts: its input is the
flattened-link state in `trf.zip`, and Mac must run the documented preflight.
Source stability and unchanged input archive hash passed. Native Mac discovery,
real-model compliance and corporate MCP remain untested. Prettier is unavailable;
no replacement installed. No Nix/OpenCode build, activation, restart, live config
edit, Git index/history change or commit was performed.

## Requirements-source preparation (2026-11-16; model/MCP acceptance pending)

The shared `evidence-v5` analysis now includes `Requirements policy: sources-v1`.
External task/specification requirements come from explicit applicable `AGENTS.md`
or the user's selected review source, never MR/host/environment heuristics. Without
such a rule, sufficient conversation/project requirements do not trigger a routine
ticket/TZ question. Source selection validates the selected target, task linkage,
contents and applicable revision; denied/ambiguous required sources stop completion
or delegated launch, not silently become technical-only review or code defects.
Delegated handoffs carry requirement sections/excerpts/provenance without changing
`dr-scope-v1`. Passive historical Chrome audits keep their evidence boundary.

`macos/trf-review/` is a durable source overlay against the user's `trf.zip`, not a
package or update to the old Mac seed. The shared corporate `opencode/AGENTS.md`
preserves the exact input bytes outside one added review/source section. Personal
reviewer frontmatter preserves its original permissions/model inheritance; its
body reads the shared analysis and delegated wrapper. Nine checked relative
symlinks share current repository sources and preserve team-to-personal placement;
the personal source links must be materialized only during a later approved export.
No `.git`, credentials, private MCP data, personal AGENTS/JSONC or CLI state were
imported from the input archive. Downloads and live Mac files remain unchanged.

47 lightweight Node checks pass: the existing 39 review/HM-evaluation checks plus
seven source-policy/wiring/baseline guards and one seeded behavior check. The
fixture demonstrably mishandles a documented string result;
that does not show a model finds it. Static guards are not an executable source
resolver, model-ordering test or native Markdown-agent/policy-loading test.
Fourteen source-selection scenarios and a paired corrected control are prepared
in `tests/fixtures/review-requirements/EVALUATION.md` but not model-run. The cheap
HM evaluation reports the existing quota-source warning; it performs no realization.
Both existing Mac audio-policy tests also pass. Tracked diff/new-file whitespace,
new local Markdown links and the unchanged input archive SHA256 were checked.
No build, activation, service restart, native runtime/PTY/browser/model or live
corporate MCP run. Prettier is unavailable; no substitute was installed.

## Same-session versus delegated review (2026-11-16; live routing unverified)

The clarified contract replaces ordinary automatic delegation: ordinary review
keeps the current conversation, agent and model, without a fork or temporary role
switch. Explicit separate-review requests use the installed delegated template;
passive recorded Chrome-MCP audits keep their specialized delegated workflow.
No keyword interceptor, new plugin, fork orchestration or report validator was added.

`evidence-v5` extracts analysis/report criteria into `config/review-analysis.md`.
HM installs that file for ordinary reviews to read; Nix embeds the same bytes in
`agents.review.system`, followed by the delegated-only `review-system.md` wrapper.
Model routes, permissions, scope defaults, canonical fingerprints and bounded
recovery remain unchanged. Empty code-review arguments still select working tree
before branch; empty Chrome arguments still select this session's latest recorded
run before the invocation cutoff. Explicit arguments take precedence.

Read-only source inspection of pinned 2.1.4 established that native subagent creation
does not copy parent history: `tool/plugin/subagent.ts:153–213` creates a session
and submits a service prefix plus the supplied prompt; `session/history.ts:103–123`
selects messages by that session ID. Common instructions are loaded separately in
`session/context.ts:126–184`; location/metadata/permissions inheritance remains in
`session.ts:275–303`. No context-clearing layer is needed, but this is not tool/OS
isolation: a permitted shell/API could retrieve other history. Parent/child share
cache affinity, not projected messages; WebSocket continuation state is keyed by
the actual session ID (`session/model-request.ts:271–290,345–348` and
`session/model-transport.ts:131–138`). No provider-side isolation guarantee follows.

Fork copies settled projected history with `parent_id: null`
(`session/projector.ts:150–219`), so it is not a normal subagent continuation.
Native `/review` submits a same-session prompt (`plugin/command.ts:42–53`).
Pinned subagent foreground is the default, unlike current docs describing
always-background behavior; these changes do not alter that native execution mode.

38 review-related Node checks pass: 14 settings/instruction/hash, nine existing
synthetic behavior-oracle and 15 Chrome checks. Guards check same-session routing,
single-source prompt composition, unchanged defaults and native-context wording;
they do not execute model intent handling, default scope resolution or context
confinement. Published hash/write recipes still run. Nixfmt ran on the two changed
Nix files; Prettier is unavailable, with no substitute installed. No new model,
native runtime/PTY/browser run, build, activation or commit; no corporate changes.
The additional existing HM evaluation test passes with decision-support enabled
and disabled; it now checks the installed shared-policy target and exact content
prefix in the configured reviewer system prompt. Total: 39 checks. This reads
source files/evaluates configuration only, not generated outputs or activation.

## Recovery/evidence acquisition refinement (2026-11-16; live behavior unverified)

The supplied experiment is a workflow failure case, not a request to re-audit its
Chrome conclusions. The revised `evidence-v4` / `chrome-evidence-v3` instructions
separate fresh-task launch from same-task recovery: no recency-based adoption of
an old child, no automatic resumption after cancellation, and no reset of the
shared ledger except a user-requested fresh independent task. Recovery uses
paginated native metadata/messages in memory rather than whole-child export probes.

Evidence acquisition captures complete responses/errors in memory. Invalid whole
CLI export permits one switch to supported paginated message reads, not repeated
exports until parse succeeds. Range/cutoff, pagination, IDs/order, tool results
and secret minimization precede the sole selected-history write. The command
publishes a small inline Python exclusive-write recipe, not a new exporter/plugin.
The shared reviewer disallows substituting inherited prose or optional follow-up
for a decisive causal link; before/after changes alone do not establish an actor.

35 lightweight Node tests pass: 12 settings/static/hash, nine existing synthetic
behavior-oracle and 14 Chrome checks. Three Chrome tests execute the exact published
write recipe against malformed JSON, byte/permission preservation, existing files
and symlinks. They verify that recipe, not model compliance, actual session-export
completeness/redaction, API fallback or recovery decisions. Two additional guards
check lifecycle/acquisition wording. `git diff --check` passes. Prettier remains
unavailable; no substitute formatter. No build/activation/commit, new model/OpenCode
runtime/PTY/browser run, corporate edit or Downloads artifact modification.

This is still an instruction workflow, not a sandbox: unchanged `edit=deny` does
not prohibit arbitrary shell writes. No claim of guaranteed semantic review or
hard tool isolation follows from these tests. A separately authorized bounded
model/native scenario is required for behavioral acceptance of this revision.

## Chrome audit alignment (2026-11-16; model acceptance pending)

The Chrome command now uses only the existing `review`, with no `general` fallback,
model override or second intent-triggered child. Global AGENTS directs explicit
ordinary-language requests to audit recorded Chrome-MCP test reporting through
the applicable installed Chrome orchestration template before a generic review
handoff, respecting project overrides, export/privacy and native permissions.
Development mentioning MCP and live browser-test requests do not select this
passive workflow. This remains model instruction routing, not a deterministic hook.

`chrome-evidence-v2` requires the decisive recorded requirement/action/observation/
claim path and counterevidence before an audit blocker. The shared review prompt
clarifies that its source/type checks apply only to source-review scope: a passive
audit does not demand source access, compilation or live retesting. Its verdict
concerns claim support, not product readiness; honest failed-feature reporting may
pass. Claim statuses, manifest recipe, privacy/export boundary, native recovery
budget and browser prohibition are unchanged. Corporate/Downloads files were not
edited and the old portable Chrome package still contains v1.

30 lightweight Node checks pass: 12 settings/static/hash, nine existing synthetic
behavior-oracle checks and nine Chrome guards/hash/fixture-integrity checks. The
three added guards cover instructions only, not live intent routing, reviewer
classification or model compliance. `git diff --check` passes. No build, activation,
service restart, model/native runtime/PTY or browser run. Prettier is unavailable;
no replacement was installed. The blind acceptance protocol is updated but unrun.

## Explicit review routing and evidence-v3 (2026-11-16)

There is still one `review` subagent, with `review-system.md` loaded as its system
prompt. Global AGENTS now directs explicit present-tense review requests to it
without model overrides or changing the parent's selection. Intent exclusions
cover discussion/quotations, future/negated requests, development/self-checks,
explicit no-delegation and duplicate command-owned launches. This is instruction
routing, not a deterministic interceptor or proof of weak-model compliance.

Analysis/verdict criteria are owned by the shared reviewer; the duplicate analysis
block was removed from `/delegated-review`, retaining scope/recovery/reporting.
The command no longer falls back to `general` when `review` is unavailable. The
evidence-v3 prompt requires the decisive implementation path before a blocking
finding, types/wrappers/host injection and spread order, attempted falsification,
and tracing proposed fixes through adjacent paths. It rejects architectural taste
as a blocker without an applicable mandatory rule or material impact. Compilation
is selected for a concrete uncertainty, subject to cost/side effects/permissions,
not required on every review. Model routes and permissions are unchanged.

27 lightweight Node tests pass: 12 settings/static/hash guards, nine existing
synthetic behavior-oracle checks and six Chrome checks. New text guards cover
declarations, not actual intent classification, full-path analysis or model quality.
The acceptance protocol now includes ordinary-request routing and paired modal
wiring/fix scenarios; no new model/native runtime/PTY run was performed. No build,
activation, service restart, corporate config or Downloads artifact changes.
Prettier is unavailable; existing layout is preserved without a replacement.

## Main config filename (2026-11-14)

Home now declares `opencode.jsonc` as the target of HM's existing generated
`opencode.json` entry, matching the current external Mac configuration. Native
`programs.opencode.settings` generation and merging stay intact; no second config,
custom generator or migration hook is added. HM's normal old-generation cleanup
removes the former managed link; it deliberately preserves unrelated manual files.

One lightweight test evaluates the pinned HM modules with a package placeholder,
without building or activating anything. With decision-support both enabled and
disabled, before/after merged settings and generated source paths are identical;
only the managed config target changes, with exactly one JSONC target and no JSON
target. The optional installed-generation runtime harness now expects JSONC and
rejects even a dangling legacy JSON link. That runtime harness and actual HM
activation/removal were not run; generated files were not built/read for this test.
The filename test plus ten logger-disable/TUI declaration and dialog tests pass;
Python syntax and whitespace checks also pass. Nixfmt and Prettier ran on changed
files; Ruff is unavailable, so the two Python edits preserve existing layout.

## Delegated review configuration (2026-11-12)

HM now declares `commands/delegated-review.md`; the existing `review` agent reads
`config/review-system.md`, retaining its configured model route, subagent mode
and edit/subagent/todowrite denials. No other agent, model table, binary patch,
plugin or corporate configuration is changed. Original Downloads artifacts and
the separate portable draft are preserved. See [DELEGATED-REVIEW.md](DELEGATED-REVIEW.md).

Initially four lightweight tests in `tests/test_delegated_review.mjs` passed: actual standalone
Nix settings evaluation validates the loaded prompt/model/permissions; text guards
validate the command's orchestrator/no-model frontmatter, HM source declaration,
bounded recovery and incomplete-report instructions. Text guards do NOT execute
recovery or prove model compliance. The source-derived semantics are from pinned
2.1.4, not a runtime concurrency experiment. Nixfmt 1.5.0 is available; Prettier is
unavailable, with no substitute formatter. Both existing Git-offline fixtures
also passed; command bytes and reviewer body then matched the separate portable
draft (subsequent refinements are repository-only). At that initial stage no build,
activation, native command discovery, model call, mock failure/recovery or live
provider test was run.

Subsequent user-run acceptance and read-only audit: parent session
`ses_e2eec9478ffe7dZYLjivJYJUzY` and child `ses_e2ee8930affeXoIdg31nKcD8jM`
show actual same-child INCOMPLETE → continuation → COMPLETE. All recorded HTTP
responses were 200; transport records show Big Pickle for parent and reviewers,
despite the child's stored configured model field showing Sol. A premature child
was interrupted after user correction before the actual command. Tracked diff
and the two relevant untracked-file hashes match the start of the test; no repo
edits/commits/builds/activations appear in the complete inspected tool history.
Two temporary files outside the project were written. This is not proof of a
sandbox, provider-failure recovery or complete instruction compliance.

The audit also found incorrect shared-budget reporting, an underspecified hash
recipe and staged/untracked confusion. The revised command/profile now require
canonical `dr-scope-v1` JSON plus exact recipe (no brute-force encodings), explicit
invocation/additional/provider counters and no premature run on a preparation
request. A partial-report continuation consumes one of six additional slots;
provider retry count only selects backoff and never adds slots. Five settings/
instruction/hash-recipe tests, two Git-offline tests and four cheap fixture-unit
checks pass. These are not proof of revised model compliance. Prettier/Ruff are
unavailable; no replacement formatter is used.

After explicit approval, `tests/test_delegated_review_runtime.py` passed both
native cases with the installed binary: private HOME/XDG/project/server and local
Responses mock, actual command discovery/expansion and native subagent/read/shell
tools. One HTTP 429 was absorbed within a single child invocation. Eleven HTTP
429s exhausted the pinned ten native retries; the scripted parent received the
terminal error, ran actual `sleep 20` and resumed the same child. Both cases have
one child and one completed read, with the result preserved without rereading.
The terminal case's invocation gap is 20.304s. All 5/17 HTTP requests respectively
used the mock `big-pickle` model ID, not a live provider. Private artifacts:
`/tmp/opencode/delegated-review-runtime-yjqaiucn/`; exact session IDs are in
DELEGATED-REVIEW.md. Two earlier harness failures did not reach these cases:
missing optional MCP (`_lpe8fpp`) and discovery before asynchronous activation
(`8hk0s7oh`). Optional-key handling, bounded discovery waiting and setup cleanup
are corrected; the latter also has a unit regression. Native phase remains bounded
to 240s, plus short setup/cleanup. No builds, activation or shared-service changes.
This tests transport/native mechanisms, not real-model orchestrator choices,
completed review analysis, later backoff steps, missing-ID/replacement recovery or
exhaustion of the seven-invocation/ten-minute command budget.

A second user-run Big Pickle smoke (parent `ses_e2ecce9dbffeYUvXNihLTXgmdv`,
child `ses_e2ecac52bffexPSz0g6i9k9QUd`) confirms waiting for the actual command,
one reviewer invocation, exact two-file scope and reproducible fingerprint,
correct 1/7, 0/6, six remaining, zero provider retries, and preservation of the
complete report/findings. Transport logs show Big Pickle only, with 8/7 parent/
child HTTP responses all 200. Runtime was 400.301s overall, 275.785s in the child:
small scope did not mean short reasoning. The parent wrote a temporary helper
script outside the repository; this was not strictly write-free. No project edits.
Private audit: `/tmp/opencode/delegated-review-live-audit-kq76wlnx/`.

User-authorized follow-ups now clarify initialization before the first invocation
only, prohibit agent-created temporary review artifacts for parent/reviewer and
explicitly forbid all three final verdicts for incomplete coverage. Six settings/
instruction/hash tests, two Git-offline tests and four fixture-unit tests pass.
These guards are not a new real-model run of the stricter artifact restriction.
The previous native mock still covers unchanged transport mechanisms, not revised
prompt compliance; it was not rerun. No build, activation or corporate Mac edits.

## Review-analysis revision (2026-11-13; live acceptance pending)

A user-supplied same-start comparison and follow-up exposed a missed caret path
and an inadequately justified APPROVE despite an unresolved material email
requirement. Both reviewers found the missing email concealment. The observed
missing highlight does not establish the later proposed watcher diagnosis.
Unknown-ID and subject concerns were not all confirmed defects. Earlier recovery
tests never established preservation of defect-finding quality.

The prompt now leads with expected behavior, representative stateful/user paths,
cross-branch comparison and counterexamples, including possible self-repair by
later callbacks. Verdicts distinguish material defects/decisive contract questions
from optional improvements, sourced accepted risk and unrun runtime checks. Parent
validation may request a reasoned resolution, not silently change the child's
verdict. The child does not receive the full command/recovery ledger. Native
recovery, fingerprint, model route and permission declarations are unchanged.

Eight settings/static/hash tests pass (two new guards failed before the change).
Seven tests in `test_delegated_review_analysis.mjs` execute seeded and corrected
synthetic candidates, including intentional-overwrite/unknown-ID/subject negative
controls. These validate the **exercise oracle**, not real model analysis or
native DOM/Vue behavior. The blind two-candidate protocol and scoring criteria are
in `tests/fixtures/delegated-review/EVALUATION.md`. No live reviewer A/B comparison,
native runtime/PTY rerun, build or activation has been performed for this revision.
Prettier remains unavailable; no substitute was installed. The second Chrome-MCP
audit scenario in the user's archive was only identified, not changed/tested.

The user subsequently supplied a live same-diff run and full handoff. Its expanded
command exactly matches the first analysis revision; review selected `review` and
returned REQUEST_CHANGES for email and a caret finding, but downplayed the latter
by extending accepted overwrite semantics. The raw child report contains that
inference before translation. The handoff incorrectly summarized unknown-ID
reject as ignored (restore still occurs), and called a blocked typecheck "clean
apart from" its environment error; the child dropped the qualifier. Worktree
location changed the manifest, not the reviewed historical diff. The effective
child system prompt was not included, so its precise version is unverified.

The current `Review policy: behavior-v2.` refinement bounds acceptance/correctness
to specific effects and scenarios, separates handoff requirements from code
observations, and preserves failed-check qualifiers. It does not force higher
severity or deduplication where the product allows overwrite. Ten static/settings/
hash and nine synthetic-oracle checks pass, including two new interleaving controls;
the two added text guards failed on the previous revision. No live run of this
refinement, build or activation was performed by the agent. A separate four-file
Mac candidate is in `~/Downloads/delegated-review-mac-2026-11-13-scenario1-r2/`;
earlier packages and supplied exports/archive are preserved. Chrome was deferred at
that stage. A later user-supplied behavior-v2 run matches the command bytes and
original diff/manifest, carries the new marker and retains email REQUEST_CHANGES
and the caret finding without the broad Wall/idempotence exemptions. This is one
limited positive case, not general quality acceptance. Filtered tsc with TS2688
still does not establish a clean typecheck; history restore remains contract-dependent.

### Chrome evidence audit (2026-11-13)

The subsequently authorized Chrome scenario adds a self-contained native Markdown
command and HM file declaration, without changing shared reviewer/routing. Its
`chrome-evidence-v1` contract distinguishes action effects from fixture legitimacy,
claim support/contradiction/absence/contamination and complete audit from missing
required evidence. A parent-only private export exception does not permit child
writes, browser actions, secret exposure or live re-testing. `drc-scope-v2` binds
the primary/supporting bytes and provenance/limitations; matching hashes do not
authenticate the source. Recovery retains one initial plus six shared calls.

Six Chrome tests pass: instruction/declaration guards, executable canonical hash
recipe and integrity of eight synthetic oracle cases. These do not execute a model
classifier, native export or Chrome browser. The 27-test combined Node run and four
Python fixture tests pass; pinned nixfmt 1.5.0 checks the changed Nix module. No
new builds, runtime/PTY/model/browser run or activation. Prettier remains unavailable.
The separate three-file Mac candidate is
`~/Downloads/delegated-review-mac-2026-11-13-chrome/`; older packages/archive and
corporate configuration are preserved. Native export completeness/redaction,
Chrome recovery, effective Mac runtime and real-model audit quality remain unverified.

## Background-tab attention ownership (2026-11-12)

The user isolated missing audio/outer urgency to inactive internal OpenCode tabs.
Installed helper and binary patch inputs match the old route-only policy; an
in-memory call reproduces its rejection of an inactive tab and its children.
The user heard both direct playback of the configured completion file and the
native question-form sound. This is not evidence that completion audio was broken.

The replacement policy retains open background session families and assigns one
live owner by last explicit route/terminal focus selection. Native sound remains
native; the existing silent Kitty helper remains separate from mute. Shared tab
membership alone never claims ownership. Private Linux runtime records use atomic
publication and PID/start-time validation; per-event decisions/receipts prevent
cross-window/channel races from duplicating output. Output can be lost on a crash
after consuming a receipt; this is not an exactly-once transport.

Lightweight checks execute the actual helper, apply the actual notification patch
to pinned 2.1.4 without fuzz, and run native handler/quiet-urgency fixtures. The
fixture replaces only the plugin wrapper, Solid effect scheduling and audio/Kitty
sinks. A separate two-process Linux test exercises real atomic IPC, concurrent
event delivery, owner transfer and abrupt owner death. Neither is a real TUI test.
The PTY harness now includes background-tab/home retention and ownership transfer;
only its Python syntax was checked, not execution. No build, activation, service
restart, installed-plugin reload or live audio/Waybar/Kitty acceptance was run.
Prettier and Ruff are unavailable; no substitute formatter was used.

The user subsequently reports that the revision works live and authorizes a
local commit after final review. This accepts the reported background-tab
notification scenario, not independent agent UI observation or the full
multi-window/focus/close/crash/mute matrix. Final read-only review found no known
commit blockers; all six policy/actual-handler/two-process tests and three silent
urgency fixtures pass again, as do PTY-harness Python syntax, backport inventory
coverage and non-patch whitespace checks. The agent did not rebuild/reactivate
or run the opt-in PTY suite. Exact unified-diff context whitespace is retained.

After user review:

1. Build only the affected HM output:
   `nix build .#homeConfigurations.samov-laptop.activationPackage`.
2. A separately approved PTY run can use
   `OPENCODE_TEST_HM_GENERATION=(realpath result) python3 home/apps/opencode/tests/test_attention_tui.py (realpath result/home-path/bin/opencode)`
   in Fish. It uses a private server/mock provider and no actual sound; it also
   exercises the existing todo scenarios. Do not run it automatically.
3. Apply HM with `home-manager switch --flake .#samov-laptop`, then close/reopen
   every TUI to load the changed built-in code. Do not restart the shared server.
4. In two Kitty windows, test inactive-tab completion/question/permission/error,
   another workspace, transfer by selection/focus, closing the owner, mute/unmute
   and children. Expect one native sound plus silent outer urgency in the owner,
   no output in the other window, unchanged internal unread indicators. Revert
   the HM generation and reopen TUI if delivery/ownership regresses. Other home
   hosts and the official-binary corporate Mac are not established by this test.

## Latest review status (2026-11-02)

The manual-selection helper-stack redesign below is a subsequent change. All
73 Node unit tests passed, including production patch application, state/selection
functions, and dialog ownership/lifecycle regression guards. The user built and
applied Home Manager and reported that TUI startup works after the fix below.
The installed binary's derivation inputs were compared byte-for-byte with the
current manual-routing patch, model-variants patch, and routing helper; all match.
No additional agent-run build was performed. Isolated runtime, actual dialog
interaction, and PTY checks were not rerun for the redesign. The following bullets
describe the earlier review of commit `5aec1de`, not verification of the redesign.

The first user-run rollout of the redesign crashed at startup with
`useDialog must be used within a DialogProvider`; the user rolled back.
`LocalProvider` wraps `DialogProvider`, so it cannot acquire that hook during
initialization. The fix removes the hook from Local and binds App's existing
dialog instance with cleanup instead. Unit regression guards check the actual
provider order, hook ownership, and chooser binding/disposal. The user's successful
startup check does not replace full runtime/PTY verification.

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

### Terminal theme versus stale palette cache (2026-11-09)

The user confirmed Blueman after the GTK alias fix, but both an existing and a
new OpenCode TUI stayed dark in a light desktop. Read-only diagnostics found
portal color-scheme 2 and Kitty background `#fafafa`, while TUI cell colors were
dark Flexoki. CLI preferences were already `flexoki` / `system`; the saved
`system-theme` palette still had the old dark terminal background `#2c2e34`.
Only appearance fields/color codes were inspected, not terminal text or secrets.

With explicit approval, an isolated installed-binary PTY reproduced the cause:
without cached colors, native renderer mode, TUI mode and Flexoki tokens all
follow light → dark → light. Seeding an opposite dark cache makes startup report
renderer light / TUI dark. Repeating the same light notification does not repair
the divergence; an actual dark → light cycle does. The test uses a private server,
temporary HOME/config/state and synthetic terminal replies, without model prompts,
personal credentials, real desktop writes or package acquisition.

`patches/theme-mode-cache.patch` puts the freshly detected renderer mode before
cached palette inference during startup, after explicit light/dark locks.

```fish
node --test home/apps/opencode/tests/test_theme_mode_cache.mjs
python3 -B home/apps/opencode/tests/test_theme_mode_tui.py /path/to/built/opencode
# Negative control only, with the old unpatched binary:
python3 -B home/apps/opencode/tests/test_theme_mode_tui.py /path/to/old/opencode --expect-stale-cache-bug
```

All four policy tests pass: real patch application followed by executing the
patched startup block with controlled dependencies, both stale-cache directions,
explicit locks, unavailable-terminal fallback and existing fallback preservation.
This is not full Solid/OpenTUI integration. The saved PTY test passed fresh-cache
and stale-cache negative controls on the old installed binary; its normal regression
mode intentionally fails there at renderer light / TUI dark. It checks real public
theme/renderer state and Flexoki text tokens, subscription and unchanged preferences,
not visible rendering in a real Kitty. The user subsequently built the HM output.
The documented relative binary path first exposed a harness bug: Popen resolved it
against temporary HOME. The harness now resolves and validates the binary path
before changing cwd. Rerunning the exact relative-path command against the user's
built result passed both fresh-cache control and stale-cache regression, including
native renderer/theme state and Flexoki tokens. No additional build was run by the
agent. A subsequent live test found a second, terminal-side bug: Kitty 0.47.0
updated colors then raised `TypeError: argument 1 must be str or None, not tuple`
in its background-image runtime call, before notifying its subscribed child.
Separately authorized one-call tracing captured the exception. With a temporary
upstream Kitty backport in that diagnostic terminal, the user confirmed live F11
both ways; protocol-only observation confirmed real notifications and renderer/theme
mode changes. All temporary Kitty replacements/tracing were restored and the
opt-in TUI observer disabled. The user then chose to remove the local Kitty
backport, overlay and its dedicated tests rather than maintain a temporary fix
before migration. That package was never built/activated. Stock Kitty 0.47.0's
live-switching limitation on Acer is accepted until an update; verify Kitty ≥0.47.1
and F11 on Lenovo using the [existing checklist](../../../docs/laptop-audit/lenovo-checklist.md).
The independent OpenCode 2.1.4 startup-cache fix and its regression tests remain.
Use the HM build/application steps
in [README.md](README.md). This client-only patch needs reopening the TUI, not a
shared-service restart. The independent corporate Mac archive is unchanged.

### Token-sharing quota fallback (2026-11-07)

`chatgpt-token-sharing` has no confirmed source of subscription window percentages
or reset times. A live diagnostic returned HTTP 401 from `wham/usage` with an
unexpired sharing token; the user switched to legacy OAuth and confirmed quota
data returned. This is evidence for the limitation, not live verification of the
new fallback. Track [openai/codex#54219](https://github.com/openai/codex/issues/54219)
and the official API references in [README.md](README.md).

The fallback shows `Limits: not exposed by token sharing`, retains active worker
counting and manual checkpoints, and skips legacy quota HTTP/cache/WS ingestion
and reset. Credential-switch events invalidate client status; legacy account
snapshots and latches remain isolated and usable when selected again.
Unit/mock regressions cover zero incompatible requests or cache creation, ignored
sharing WS data, waits/completion, checkpoint readiness/reset, credential-switch
notifications, hiding legacy snapshots/latches and restoring the selected account.
An in-flight legacy HTTP result is also rechecked against the current identity:
switching to sharing or another account cannot restore the old percentages.
The TUI fixture checks the placeholder on both slots, absence of stale percentages
and markers, transition back to legacy, and explicit checkpoint commands.

Home Manager adds a static evaluation/build warning and a pre-write activation
warning (`warnEcho`, yellow on color-capable terminals unless `NO_COLOR` is set).
Neither queries GitHub/API nor reads authorization. Remove the reminder only after
real token-sharing percentages, window duration/reset data, account switching and
per-window warnings are verified; issue closure alone is insufficient.
Build, activation, installed layout, live fallback switching and actual TUI/PTY
verification remain user-run; they were not performed for this fallback.

Completed: all 19 limits/TUI tests and the combined 72-test
limits/TUI/todo/model-calls/model-routing suite passed, with no skipped tests.
Nix parsing, isolated reminder-module evaluation with the pinned HM library,
generated activation-shell syntax, declared formatters and `git diff --check`
passed. The isolated evaluation uses stub package/config arguments, not a full
Home Manager profile evaluation. No build, activation, service restart or
authorization change was performed by the agent.

### UI-only budget signals and todo capacity (2026-11-05)

This supersedes automatic model warning/wrap-up behavior described in the earlier
regression below. Budget observation no longer modifies model instructions or reads
checkpoint metadata; the TUI draws a triangle beside each affected window's
percentage: gray for the early threshold, yellow for the main threshold or a
persisted latch. Both windows can have independent markers; healthy/dismissed
windows have none. There is no separate warning field or command hint.
Only the explicit `/checkpoint` command requests handoff work. The checkpoint request text
is unchanged and has been shown to the user for wording review.

Five-hour thresholds are unchanged. Weekly thresholds are each scaled by `3/22`
and rounded independently, based on one ~39-minute observation: 22 five-hour pp
versus 3 weekly pp. For 1/2/3 active workers the weekly early/checkpoint thresholds
are 3/2%, 4/3%, 5/3%. Existing latches intentionally survive threshold changes;
manual `/limits-reset` dismisses them for the current limiting windows. Old model
`notices` are not loaded and disappear on the next cache write.

Todo capacity is now 128 KiB, without automatic prompt inclusion or Markdown
restructuring. Tests cover exact-limit reads, structured additions above 32 KiB,
byte-identical unrelated note preservation, UTF-8 byte limits, and rejection when
generated metadata pushes a proposal over the limit, before any consent form.

The 16-test limits/TUI unit/mock set passed after the per-window marker change;
the earlier combined limits/TUI/todo/model-calls/model-routing set passed 68 tests.
Coverage includes per-window
worker-dependent thresholds, frozen model instruction arrays in normal/warn/reserve
states, legacy latch persistence without notices, independent gray/yellow TUI
markers (including both windows at once),
and no automatic prompts. These are public-API-shaped fixtures, not a real PTY.
No build, new native runtime, live quota or installed HM-layout verification was
run for this redesign; the native results below predate it.

### Limits regression follow-up (2026-11-05)

The first limits rollout displayed the indicator but failed prompt admission with
HTTP 500. The server log identified `session.metadata[checkpointKey]` in the prompt
hook: `Session.Info.metadata` is optional, but the original fixtures always supplied
it. Server reads now use optional access. A new unit regression reproduced the
original failure before the fix and covers metadata-free prompt/tool hooks,
wrap-up, checkpoint creation and resets.

The targeted native runtime also exposed that `checkpoint_ready` was only available
through Code Mode despite instructions calling it directly. It now explicitly uses
`codemode: false`. The isolated `--limits` run passed with the existing installed
binary and copied current plugin sources: real HTTP prompt admission without
metadata, a successful native tool call, checkpoint tool execution and reset on
the next prompt. Responses came only from a localhost mock; no personal service,
credentials or database were used or changed. No agent-run build was performed.
This does not cover live OAuth/quota, the HM-built plugin layout or real TUI/PTY.
The 25-test limits/TUI/model-calls/model-routing unit/mock set also passed.

```fish
env -u OPENCODE_TEST_HM_GENERATION python3 home/apps/opencode/tests/test_v2_runtime.py (command -v opencode) --limits
```

### General checks

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
set generation (nix build --offline --no-link --print-out-paths path:.#homeConfigurations.samov-laptop-old.activationPackage)
env OPENCODE_TEST_BINARY=$binary OPENCODE_TEST_HM_GENERATION=$generation python3 home/linux/modules/hyprland/tests/test_context_tui.py ContextTui.test_opencode_real_tui_plugin
env OPENCODE_TEST_HM_GENERATION=$generation python3 home/apps/opencode/tests/test_v2_runtime.py $binary
env OPENCODE_TEST_HM_GENERATION=$generation python3 home/apps/opencode/tests/test_attention_tui.py $binary
# Fast targeted check of the HM-built urgency package without building every home package:
set urgency (nix build --no-link --print-out-paths --impure --expr '(builtins.getFlake ("path:" + builtins.toString ./.)).homeConfigurations.samov-laptop-old.config.xdg.configFile."opencode/plugins/quiet-urgency".source')
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
- Manual selection maps configured Sol/Luna to Paid helpers and Big Pickle to Free;
  unknown identities require a Free/Paid choice, with cancellation leaving policy
  and drafts unchanged. Production-patched functions cover the native chooser's
  select/cancel callbacks, lookup/write failure, retry, cycles, overlapping actions,
  route/agent changes, and missing helper models. Session/agent overrides survive
  serialization without leaking into siblings or auxiliary roles. Effort changes
  retain helpers and do not save global preferences; legacy global variants cannot
  override configured agent defaults. Home policy is passed into native session
  creation. Explicit mode commands reset all overrides; automatic agent switching
  preserves them. The picker awaits selection before inspecting variants.
  The Local/Dialog provider-order guard prevents acquiring a child provider hook
  during Local initialization; chooser binding fails closed before setup and after
  cleanup without letting stale cleanup detach a newer binding.
  The baseline metadata-only free→paid test passed
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
reload without implicit approval, independent priority/visit counters, same-user-turn
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

Organizer unit fixtures cover explicit-only stable sorting (In progress/Todo/Done,
priority, visits, oldest-created and newest-completed), unknown dates, lifecycle
transitions/reopening, observed manual closure, totals, local Git date backfill,
legacy English-label migration, preserved heading numbers and fenced artifacts.
Language defaults and artifact-preservation instructions are checked as contracts;
these tests do not establish how reliably a live model recognizes artifacts.
All 38 local todo unit tests passed. Manual installed-plugin smoke on 2026-11-04
exercised read → sort proposal → native consent → one saved local commit; the user
reported the result looked correct. This covers that real migration/sort/approval
path, not every lifecycle transition. The full isolated runtime/PTY suites were
not rerun for this extension; older runtime/PTY evidence does not cover it.

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

Historical `archive/decision-support/tests/decision-check-scenarios.md` supplies behavioral fixtures for manual/model
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

## Approval-sensitive Git mutations (2026-11-14)

The user approved extending commit Ask to history/integration/checkout/discard
operations, stash mutations, destructive/ref-changing branch/tag operations and
worktree cleanup. Native permissions retain literal command boundaries, so
`merge-base` is not `merge`. Direct inspection exceptions preserve comparisons
even with refs named `rebase`; no broad `git * diff *` allow can hide a reset.
Instructions require explicit operation consent, separate flags and no Always.
Read-only agent restrictions, provider/tool policies and git-offline are unchanged.

Eight approval declaration tests and two existing offline tests pass. They cover
ordinary and option-prefixed mutations, implicit stash push, ref/worktree changes,
branch/tag/worktree inspection, graph comparisons and mutation operands named
after inspection commands. The conservative `git -C /repo diff main rebase` Ask
is explicit fixture coverage: native wildcard rules are not a Git argv parser.
They do not sandbox aliases/wrappers or exhaust every combined flag form.
Four additional external-package tests execute the extracted pinned 2.1.4
matcher/evaluator, compare the declaration matcher across the command fixtures,
and verify corporate/home rule equality, provider preservation and the saved
Always caveat. Both Mac patch variants apply/reverse on original and comment-
refined personal rules (four fixture combinations), without touching live config.
No native permission UI, shell-scanner integration, live saved-grant update,
build, activation, service restart or new commit was performed.

## Limits reconnect and explicit commit policy (2026-11-13)

Read-only live diagnosis found fresh local cache and `local.limits/status` while
the user confirmed the TUI stayed stale, including after `/reload`. The surviving
TUI's log shows the 00:55 UTC disconnect and native reconnection. An in-memory
probe of the exact installed 2.1.4 Promise RPC and SharedEvents sources, with
mocked transport only, reproduced a permanently ended RPC callback despite a
working replacement event subscription and status reads. This does not establish
every possible cause of stale UI or independent checkpoint failure.

The prepared fix uses the host data stream and re-reads limits/current checkpoint
after `server.connected`, without idle polling. The TUI fixture rejects one-shot
RPC listeners and checks missed-event catch-up, subsequent updates, concurrent
reconnect coalescing, metadata isolation, and disposal during a pending read.
Checkpoint text now requires a separate explicit commit request and accepts a
reviewed, explicitly uncommitted handoff. Native shell declarations ask for
`git commit` (also with Git options), not other Git commands; saved Always grants
can override Ask and arbitrary wrappers are not a sandboxed guarantee.

All 22 targeted limits/TUI/commit/offline tests pass with the installed TypeScript
transpiler; commit matching is a declaration fixture, not a native permission UI
test. No build, activation, live fixed TUI/PTY, service restart, or commit was run.

## Saved permissions command naming (2026-11-14)

The command is now **Allowed permissions** in the native Ctrl+P palette and
`/allowed-permissions`, without retaining the ambiguous `/permissions` alias.
Only public command metadata changed; plugin/command IDs and the saved-grant
controller, API scope and native dialogs remain unchanged. All 23 controller/TUI
fixture tests pass, including the single palette/slash registration. This is not
Mac/OpenTUI runtime acceptance or a new binary patch.

The final external Mac patch targets the already-applied
`opencode-mac-permissions-2026-11-14.patch`: Git approval expansion, append-only
personal consent rules and the existing TUI plugin's two naming fields. It
applies/reverses on original or comment-refined personal rules; repeated apply
refuses without changing files. Other corporate JSONC fields, including policies
and providers, remain unchanged. It does not reinstall the previous overlay.

## Saved permissions TUI (2026-11-13)

The TUI-only `/permissions` plugin uses public native `dialog.select()` and
`dialog.confirm()`, the connected client's location lookup and saved-permission
list/remove API. No custom rendering, JSX or new binary patch is needed. Ctrl+D
or Enter requests confirmation; only explicit `true` authorizes removal. q/Esc
closes the list; Cancel/Esc or dialog replacement cancels confirmation. Completion
uses a native toast, never automatically reopens the list over another dialog.

Scope is frozen to the opening directory/project; unloaded session locations do
not fall back to the launch project. The controller independently filters project
IDs, serializes operations and revalidates displayed ID/project/action/resource
after confirmation, immediately before deletion. Scope mismatches and disposal
refuse subsequent operations; they do not automatically clear an existing native
dialog. Public promise dialogs provide no ownership handle, so cleanup deliberately
avoids clearing a potentially unrelated replacement. The ID-only remove API cannot
make the preceding read atomic; already dispatched DELETE cannot be undone.

Fourteen actual-controller tests cover sorting/filtering/copying, empty/unknown
IDs, confirmation and cancellation, stale action/resource/project/disappearance,
concurrent requests, errors, refresh failure and disposal/scope changes during
loading, confirmation, validation and deletion. Eight HM/native-dialog fixtures
verify co-located plain TypeScript source bytes, public API input shapes, command
registration, selection/confirmation settlement, stale callbacks, escaping, full
long-resource payloads, hydration, duplicate opens, errors including post-delete
notification failure, scope guards and late responses without modal reopening.
No JSX transpiler is required. All 22 checks pass without builds. These fixtures
do not test real OpenTUI layout, keyboard dispatch, very-long-pattern readability,
installed HM layout or native TUI/PTY behavior. No live saved grants were deleted,
no service restarted, and no full semantic TypeScript check was performed.

The user subsequently accepted the native UI. This is user-reported acceptance,
not independent agent observation of the installed layout, every cancellation/
deletion path or very-long-pattern readability.

## Accounting limits

`opencode-task-report` opens a SQLite read-only URI and a snapshot transaction.
It detects `session_v2`/`session_message`, preferring V2 for the requested session,
otherwise retains legacy `session`/`message`/`part` and saved ledger handling.
The report includes descendants, model routes, stored usage, cache, tool states,
saved retries and compaction markers; it does not expose prompts/source text.
The home HM declaration now disables `model-calls-v2` with the native file
`enable = false`; its source/tests remain for explicit routing/effort/retry
profiling. The user subsequently applied HM and reported completing the restart.
Read-only checks confirm the installed plugin path and `local.model-calls` runtime
registry entry are absent, with the service available. The agent did not activate
HM or restart the service. Existing journals are not deleted, and the report
remains usable from session storage without the plugin.

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
The isolated runtime fixture explicitly installs the logger when testing source
plugins. With `OPENCODE_TEST_HM_GENERATION`, it instead respects whether that
generation includes `model-calls-v2` and expects no journal when it is absent.

The configured 212000 soft-input ceiling is not a proof of usable context or a
hard cap on individual request sizes. Checks happen between steps. Work High /
Plan XHigh and Explore Max remain hypotheses to compare on repeated frozen
real tasks, including children, corrections, cache and compaction.
