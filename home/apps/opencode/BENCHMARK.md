# Per-task accounting: baseline first

`opencode-task-report` reads the local OpenCode SQLite database in a read-only
transaction. It prints counters, model names and IDs, never prompts or tool output.
Use `--db` for another database. Current support: the `message` / `part` schema.

```fish
opencode-task-report --recent 5
opencode-task-report --session <session-id>
opencode-task-report --session <session-id> --turn last
opencode-task-report --session <session-id> --json > /tmp/task-baseline.json
```

An entire fresh session is the preferred task boundary. `--turn` selects a time
window between user messages, not a semantic task; child attribution is approximate
for overlapping work. Follow-up instructions may belong to the same task.

## Metrics and limits

- `processed_input_tokens`: recorded input + cache read + cache write, summed
  across model responses and linked child sessions. Output and reasoning are
  separate counters. These are OpenCode's normalized provider counters.
- `processed_total_tokens` additionally includes output and reasoning across the
  same sessions. This is the total token-work metric, not a dollar estimate.
- Keep the cache breakdown: a reduction in processed tokens is not necessarily
  the same reduction in billed cost. Report per-model totals when models differ.
- `cost_reported` is OpenCode's reported cost; zero may mean unpriced/subscription,
  not free. Provider-side hidden calls, failed requests without usage, and previously
  deleted sessions cannot be reconstructed.
- Tool output sizes and exact repeats are **characters**, not token estimates or
  measured savings. They describe stored text; pruning/compaction and protocol
  serialization can make actual model inputs different. Successful identical
  outputs are not automatically redundant evidence.
- New RLM child usage is saved before deletion under
  `$XDG_STATE_HOME/opencode/task-usage` (default `~/.local/state/opencode/task-usage`).
  Only IDs, model names, timing and usage counters are retained. If recording fails,
  the child session is preserved and a warning is logged. Standard subagents are
  followed through database parent IDs. Retained children are not counted twice.

## Experiment

1. Pick real tasks and freeze the source revision/data, model and settings.
2. Define expected findings and source references before comparing runs.
3. Run each task in a fresh session; repeat each condition at least three times.
   Keep governor and instructions identical except the feature under test.
4. Save each report after the task finishes. Record quality checks and wall-clock
   duration separately. Do not compare this long planning session with a fresh run.
5. Compare total token work, processed input, per-model cost and accuracy. Treat
   incomplete-usage reports as unsuitable for a claim about total task savings.

Target: at least 25% less per-task total token work, with no degradation on the
predefined checks. This is an empirical target, not a universal guarantee.
It is not equivalent to 25% lower billed cost: cached input and model prices differ.
This change adds measurement, not a claimed optimization. Select the next
optimization only after inspecting repeated outputs and oversized retrievals.

Do not use `rlmRecursive = false` as a clean A/B condition: it currently gates
the entire plugin directory, including output-governor and permission-stats.
