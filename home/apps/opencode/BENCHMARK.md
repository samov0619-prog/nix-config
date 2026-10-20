# Home OpenCode 1.19.3: routing, compaction and task accounting

## Native baseline

Only the OpenAI provider is enabled; its native adapter uses Responses. No custom
classifier, model fallback or output interception is installed.

| Route | Model | reasoningEffort / variant |
|---|---|---|
| build / general | openai/gpt-6.1-sol | workEffort, default high |
| research / review (custom subagents) | openai/gpt-6.1-sol | workEffort, default high |
| plan | openai/gpt-6.1-sol-plan → API gpt-6.1-sol | planEffort, default xhigh |
| explore (bounded facts with path:line and coverage gaps) | openai/gpt-6-luna | max, hypothesis to compare with high |
| compaction / summary | openai/gpt-6.1-sol-high → API gpt-6.1-sol | high |
| title / small_model | openai/gpt-6-luna | low |

Model and agent options explicitly set `reasoningEffort`. Task selects the child
agent's model, or inherits the parent's; `small_model` does not route task or
compaction. Title uses `small:true`, which ignores the selected variant, so Luna's
model options and title's agent options explicitly select Low.

In 1.19.3, request preparation merges model options, agent options, then the source
message's variant. Compaction inherits that variant, even when its model changes.
The primary Sol exposes only `workEffort` via `reasoning_options`. The plan alias
exposes only `planEffort`, independently. The native
alias `gpt-6.1-sol-high` has API ID `gpt-6.1-sol` and exposes only High, so neither
a primary Sol Max nor Luna Max source can override compaction's High. Inspect
resolved effort and API model ID, not just the stored alias/variant label. Luna
exposes Low, High and Max. This is a model alias, not a provider or fallback.

`workEffort = "high";` controls build/general/research/review; `planEffort = "xhigh";`
controls plan. Each accepts high, xhigh or max. The TUI's selected variant is keyed
by provider/model ID (`packages/tui/src/context/local.tsx:363–387`), and explicit
input variants take precedence (`session/prompt.ts:646–654`). The separate plan
alias prevents shared variant state across configured plan/work models. Explicit
user model overrides still take precedence; verify/reset old per-agent model
selections when migrating an existing TUI profile.

Compaction/summary, Luna, permissions and context budgets remain independently
configured. Short conclusions and external AA evidence are in [README.md](README.md).
Our repeated comparison covers Luna only. The Sol plan→build pilot below has
one small task per condition, with incomplete usage; it is not a quality ranking
or a complete cost comparison.

## External Sol High / XHigh / Max evidence

The supplied `gpt-6-1-sol-comparison.md` reports a Coding Agent Index v1.5 snapshot:
High/XHigh/Max = 60.1/62.9/60.1; Codex task cost = $0.89/$1.04/$1.55; task time =
13.3/15.5/24.4 minutes. The file itself discloses that its numbers were carried
forward without independent re-verification. The numeric coding-agent chart rows
were not independently re-extracted here. Treat them as an external snapshot.

The retrieved [AA High/XHigh comparison](https://artificialanalysis.ai/models/comparisons/gpt-6-1-sol-high-vs-gpt-6-1-sol-xhigh)
confirmed Intelligence Index 50/51 and Intelligence task cost $0.32/$0.39, with
13K/18K output and 6K/9K reasoning. Those metrics are from a different evaluation
suite and do not directly establish a plan-stage or coding-agent success rate.

Do not label $1.48/$1.65/$2.58 as measured cost per successful solution: they equal
the supplied task cost divided by Coding Agent Index/100. The retrieved
[AA methodology](https://artificialanalysis.ai/methodology/coding-agents-benchmarking)
defines the index as equal-weight benchmark pass@1 averages, but cost as pooled
per-attempt averages across components with 113/66/124 tasks; missing telemetry is
excluded. These denominators/weights do not match. Reconstruct successful-task
cost from aligned attempt outcomes and costs, or report the ratio only as a
constructed efficiency indicator, not an observed success cost.

The data motivates work High / plan XHigh as a hypothesis; it does not prove
optimality, a statistically significant gain or that build High suffices for
every hard refactoring task. Compare complete plan→build workflows under
High/High, XHigh/High and Max/High on frozen real tasks, including children,
retries, corrections, compaction and cache. Keep API-equivalent estimates and
subscription quota separate; incomplete usage remains incomplete.

[OpenAI's Sol model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
confirmed high/xhigh/max, 1.05M context, 922K maximum input, 128K output, and the
272K per-request input pricing tier. The 212K overflow target and 272K pricing
boundary use different counters; stepwise checks can overshoot. Neither the
pricing tier nor advertised context proves a reliable reasoning window.
Sources retrieved 2026-10-20. No local file in Downloads was modified.

Global edit, Bash and external-directory asks and the Git allowlist are retained.
Plan explicitly denies edits; explore/research/review deny edits, task and todos.
Explore's native skill denial is retained. Research/review use the global Bash
policy, without additional allows. Verify merged agent and child-session rules;
parent agent restrictions are not automatically inherited by children.

RLM is a disabled source archive under `archive/rlm-disabled`, not an installed
tool, plugin or skill. Archived tests have `.disabled` filenames. Permission stats
is installed independently as `plugin/permission-stats.ts`, using only Node builtins.
OpenCode's internal dependencies are unchanged. Other skills, Python, rg and fd
remain available. This home module does not update the corporate Mac profile.

## Compaction and window budget

Home OpenAI auth was checked as OAuth. The local catalog declares both models as
context=1,050,000, input=922,000, output=128,000; the 1.19.3 OAuth adapter does not
reduce GPT-6 limits. These are declared client limits, not an empirical proof that
the account accepts every possible request up to the advertised window.

The baseline deliberately sets a **soft** input limit of 244,000 on both models:

```text
limit.context = 1,050,000       # unchanged
limit.input   =   244,000       # local soft ceiling
limit.output  =   128,000       # unchanged
compaction.auto = true
compaction.reserved = 32,000
compaction.preserve_recent_tokens = 15,000
compaction.prune = false
```

From `packages/opencode/src/session/overflow.ts` in 1.19.3:

```text
O = ProviderTransform.maxOutputTokens(model, runtime output cap)
R = compaction.reserved ?? min(20,000, O)
T = limit.input ? max(0, limit.input - R) : max(0, limit.context - O)
N = tokens.total || (input + output + cache.read + cache.write)
overflow = auto != false && context != 0 && N >= T
```

Here **T = 244,000 - 32,000 = 212,000 tokens**. This is the last model step's
counter, not cumulative task usage or precisely prompt length. The fallback in
the formula does not add reasoning separately; do not silently change it.
Without `limit.input`, `reserved` does not control the threshold. Do not lower
the model's output limit to force earlier compaction.

`ProviderTransform.maxOutputTokens` defaults to 32,000 in 1.19.3, but the built-in
OpenAI `chat.params` hook clears `maxOutputTokens`. The isolated Responses requests
confirmed that no `max_output_tokens` field is sent. Do not mistake the helper's
32K value for an enforced output cap on this route. The catalog's 128,000 output
limit is preserved. Reasoning shares the generation budget. At the target
threshold even allowing the full 128,000 output leaves 710,000 tokens within the
declared context for growth and protocol overhead. Verify the actual request cap,
instructions, tools and provider behavior in the isolated run.

Checks occur at completed steps / between loop iterations, not continuously.
Expect compaction on the first step crossing 212K; a large response or tool result
can jump past 225K. Retain the recent tail with native `tail_start_id`; do not set
`tail_turns`, so the 15K estimated budget controls retention. Check summary + tail
and the interval until the next compaction to detect repeated re-compression.
`prune=false` disables early tool-output pruning, not native tool truncation or
the compactor's shortened serialization of old tool outputs.

### Summary failures

`compaction.ts` marks compactor overflow as an error and stops; errors do not
publish a successful Compacted event. `message-v2.ts:filterCompacted` uses a
summary as a history boundary only when it has `finish` and no `error`. Original
database messages are not deleted by compaction.

Verify permanent API failure after retries, partial-stream failure, abort and
compactor overflow: no successful replacement and old evidence must remain in the
next effective context. Also check empty successful responses and length-limited
summaries. Native success detection is `finish && !error`, not semantic validation
of summary content. If one of those cases is accepted despite missing evidence,
record an upstream limitation; do not claim it is fixed by configuration. There
is no Hermes-style `abort_on_summary_failure` setting in this schema. The isolated
native runtime confirmed the empty-success limitation: `finish=stop`, no error.

## Manual read-only task report

`opencode-task-report` reads local SQLite in a read-only transaction. It prints
IDs, routes, counters and character counts, never prompts or tool output. There
is no LLM call, daemon, hook or periodic report. Use `--db` for another database.
Supported storage is the `message` / `part` schema, not every OpenCode DB version.

```fish
opencode-task-report --recent 5
opencode-task-report --session <session-id>
opencode-task-report --session <session-id> --turn last
opencode-task-report --session <session-id> --json > /tmp/task-baseline.json
python3 -B -m unittest discover -s home/apps/opencode/tests -v
```

An entire fresh session is the preferred task boundary. `--turn` selects a time
window between user messages, not a semantic task; child attribution is approximate
for overlapping work. Follow-up corrections may belong to the same task.

- Include native children recursively through parent IDs. Historical ledger
  counters under XDG state `opencode/task-usage` are still read without rewriting
  them; retained children are not counted twice. No new RLM records are produced.
- Prefer saved `step-finish` counters when present: a retried message can overwrite
  its message-level token counters. Never add message and step counters together.
- `processed_input_tokens` = input + cache read + cache write across recorded
  steps and children. `processed_total_tokens` also adds output and reasoning.
  OpenCode normalizes output to exclude reasoning; raw provider output may include it.
- `by_model` and `by_route` preserve model/agent/stored-variant breakdowns. Compaction
  requests, summary messages, failed messages and stored retry parts are reported.
  Retry parts do not cover all transport retries; labels do not prove effort.
- `cost_reported` is OpenCode's accumulated estimate. Zero may mean subscription
  or missing prices. Keep cache breakdown and model prices, including context tiers.
- DB reports explicitly set `full_task_usage_complete=false`: title and some
  failed/retried calls have no stored usage. Deleted/unlinked sessions and hidden
  provider work cannot be reconstructed. A completed assistant is not proof that
  the user's task succeeded.
- Tool-output sizes and exact repeats are characters, not token estimates or
  measured savings. Identical outputs are not automatically unnecessary work.

## Verification before home activation

1. Build laptop and desktop Home Manager outputs without activation; verify the
   package's `--version` is 1.19.3. Preserve the watcher LD_LIBRARY_PATH wrapper.
2. Run that package from the built output in a temporary HOME/XDG tree outside the
   real config and DB. Use the generated config, rules, skills and independent
   permission plugin. Keep credentials and raw traces outside Git.
3. Inspect `debug config`, `debug agent <name>`, `debug skill` and provider models.
   Verify OpenAI-only, efforts/variants, limit values and inherited permission rules.
   Confirm no RLM/governor in loaded tools/plugins/skills, and permission-stats loads.
4. Invoke both retained skills via native skill tool where allowed; check explore's
   denial. Check native tool-output artifact creation and reading selected evidence.
5. Exercise every route, including real task children and compaction from a Luna
   Max session. Record actual model, reasoning effort and Responses endpoint.
   Test 211,999 / 212,000 counters, summary failures and retained tail. A local mock
   validates wiring and failure handling, not model accuracy or account acceptance.
6. Do a live OAuth smoke in the isolated profile, then compare Luna Max vs High
   with the methodology below. Check watcher backend=inotify without ERROR from a
   clean environment. Restart OpenCode after Home Manager activation by the user.

## Luna High versus Max: cost of the successful whole task

1. Freeze revision/data and instructions. Predefine required findings, source
   references, correctness checks and the task's success condition.
2. Use real bounded exploration tasks with some missing/ambiguous evidence. Run
   each condition in fresh sessions at least three times, alternating run order.
   Change only explore's variant AND reasoningEffort (High versus Max).
3. Keep root Sol High, prompts, tool limits, native artifacts, compaction and
   prune=false identical. Include parent integration, children, corrections,
   compaction and retries until the **whole task** succeeds, not just the child reply.
4. Save DB reports, quality results, wall-clock duration and errors. Reconcile
   missing calls using provider usage or a verified native request trace. The
   1.19.3 test with `experimental.openTelemetry` and a local OTLP collector exported
   logs but **zero AI spans**: `tracingLayer()` is defined but has no caller in this
   source revision. Do not assume the flag alone supplies full accounting. If
   native tracing becomes usable, deduplicate outer/inner spans and retry attempts.
   The report remains a manual DB reader; no instrumentation plugin was added.
5. Keep processed-token work, per-model API cost and subscription quota separate.
   API estimates use the price/tier and cached/uncached breakdown for each request;
   compare against provider billing. OAuth zero cost is not free; token work is
   not a subscription quota meter. Record subscription usage/limits from the
   account separately; overlapping unrelated activity prevents precise attribution.
6. Select Max only if its accuracy or whole-task success cost justifies it. Do not
   claim savings from incomplete usage, a single run, different source revisions,
   or a comparison of a long planning session with a fresh task.

Pruning is a later independent experiment after this baseline is measured. There
is no preset percentage-savings target and no claimed Max advantage.

## Separate plan/work verification and live pilot — 2026-10-20

Current defaults are work High and plan XHigh. Laptop and desktop Home Manager
builds passed without activation. The generated config exposed distinct native
IDs for work, plan and compaction, with the same underlying Sol API model ID.

The isolated native Responses fixture verified every route, including a single
session switching plan→build→plan with xhigh→high→xhigh. A test executed the actual
versioned TUI variant methods from `local.tsx` (removing the TS parameter annotation)
against resolved provider models: saved plan and build selections remained
independent. This is a method-level TUI check, not a renderer/keyboard end-to-end
test. Explicit saved user model overrides still require checking on migration.
Automatic compaction from plan XHigh sent Sol High. Threshold, tail, permissions,
skills, permission stats, native artifacts and summary failure checks passed.
Fixture evidence: `/tmp/opencode/home-1193-fvicd904`.

The live OAuth pilot ran a frozen Python interval-merging task once with each
plan effort, followed in the same session by build High. It covered half-open
intervals, overlaps versus touching, empty/invalid intervals, negative endpoints,
generators and input immutability. Plans made no source changes. Edit/test asks
were answered only for the fixture implementation and its unittest command;
production permissions were not changed.

The public test file stayed unchanged. Each implementation passed 12 public
tests plus 160 held-out random cases checked by an independent overlap-graph
oracle, rather than a copy of the normal sort-and-scan implementation.

| Plan / build | Plan seconds | Whole workflow seconds | Recorded total tokens | Verification |
|---|---:|---:|---:|---|
| High / High | 11.61 | 20.25 | 41,844 | 12 + 160 passed |
| XHigh / High | 20.94 | 33.71 | 36,256 | 12 + 160 passed |
| Max / High | 27.75 | 39.70 | 37,287 | 12 + 160 passed |

Each workflow had one session, no children, no compactions and no recorded failed
assistant messages. The task was small, n=1 per condition, fixed High→XHigh→Max
order, with different cache histories and build trajectories. Title and some
transport work are not reconstructible from DB. These results verify the workflow
and measurement pipeline, not that XHigh/High is optimal or that reduced recorded
tokens imply a cheaper successful task. They do not replace the planned repeated
experiment on difficult real work. OAuth cost remained unpriced/zero; subscription
quota was not measured. Native compaction was exercised separately by the fixture.

Live evidence: `/tmp/opencode/plan-build-pilot-uwasrn2r` (plans, implementations,
public test logs, read-only DB reports and permission replies). The isolated auth
copy was removed after verification. Seven task-report tests also passed.

## Earlier one-line Sol effort switch verification — 2026-10-20

After adding `strongEffort` and the native High alias, the default High config
built successfully for laptop and desktop. A temporary copy changing only
`strongEffort = "high";` to `"max"` also built successfully for laptop.

Both generated configs passed the isolated native Responses fixture. All five
work agents resolved and sent the selected effort; compaction and summary used
the High alias with API ID `gpt-6.1-sol`. Automatic compaction from primary Sol Max
and from Luna Max sent Sol High; the 212K threshold, tail and error behavior held.
The Max fixture results are under `/tmp/opencode/home-1193-1it28l5d`.

A short live OAuth smoke accepted a Sol Max request and successfully summarized
the session through the High alias. Evidence is under
`/tmp/opencode/live-home-1193-vy__w0aa`; the isolated auth copy was removed. This
checks compatibility and availability, not a Sol High/Max quality or cost gain.
This was the earlier shared `strongEffort` design, superseded by independent
`workEffort` and `planEffort` above.

## Initial baseline verification results — 2026-10-20

- Home Manager laptop and desktop builds passed without activation; package 1.19.3.
- Isolated native runtime with a local Responses fixture verified all route
  models/efforts, actual task children, Sol High compaction after Luna Max, the
  211,999/212,000 boundary and native tail retention. Only OpenAI was enabled.
- Retained skills loaded through the native skill tool; explore's skill denial
  held. A real permission request/reply wrote the independent permission-stats
  JSONL. A large Bash result produced a native `tool-output` artifact. No RLM or
  custom governor was installed in the isolated tree; watcher backend=inotify.
- Permanent API failure, compactor overflow, partial-stream failure and abort
  stopped compaction and preserved original evidence in the next model request.
  An empty successful summary was accepted by upstream; this is not a
  configuration-level guarantee against empty summaries.
- Seven report tests passed, including read-only SQL, native/legacy child
  deduplication, cache counters and multiple finished steps of a retried message.

A live OAuth comparison ran the same frozen two-file configuration fact-check
three times per condition, balanced order High/Max, Max/High, High/Max. Each task
used Sol High, exactly one explore child, and parent verification/integration.
All six final answers met the requested facts, formulas, references and evidence
limits. There were no recorded failed assistant messages or compactions in these
small tasks. The answers described the frozen source's Max configuration in both
conditions; the *running child* used High or Max as verified in resolved agents
and stored route counters.

| Condition | Successful tasks | Median seconds | Median recorded total tokens | Median API-equivalent USD, recorded calls only |
|---|---:|---:|---:|---:|
| Luna High | 3/3 | 60.20 | 40,629 | 0.048568 |
| Luna Max | 3/3 | 73.79 | 40,527 | 0.036418 |

API-equivalent figures use the local catalog's base input/output/cache-read prices
per million: Sol $2/$10/$0.10, Luna $0.10/$0.50/$0.01. All recorded requests were
below the 272K context tier. OAuth reported cost was zero; these are estimates for
the recorded root+child work, not billed API cost or subscription consumption.
Cache reads varied (High 11,904–21,888; Max 15,744–18,688 tokens per task), and root
behavior varied. Title usage is missing and native trace reconciliation did not
work. Therefore this is a preliminary comparison, not proof of full-task savings
or a Max accuracy advantage. Retain the requested Max hypothesis pending broader
tasks and complete provider-side accounting.

Raw isolated fixtures, DB reports and answers are outside Git under
`/tmp/opencode/home-1193-nt7wkx7o` and
`/tmp/opencode/live-home-1193-f9ibuaju`. Isolated credential copies were removed
after verification. Initial harness setup failures were separate from the six
successful comparison runs and do not establish model performance.
