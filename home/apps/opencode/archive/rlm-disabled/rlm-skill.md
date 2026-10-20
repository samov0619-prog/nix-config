---
name: rlm
description: Aggregate evidence across files or extract focused information from large text sources without loading their bulk into the conversation. Use when ordinary targeted searches and short reads are insufficient.
---

# RLM — Bounded Source Analysis

## Choose the Right Tool

Follow the source-exploration policy in global `AGENTS.md`. Filename discovery,
targeted searches, and short reads remain normal tools; there is no call-count
threshold or requirement to invoke RLM for every multi-file question.

Use `rlm` when programmatic aggregation or extraction will reduce the source
material entering the conversation. If repeated searches stop producing new
evidence, narrow the question or switch approaches rather than repeating them.

## Workflow

1. Select the narrowest relevant file or directory. Do not load a home directory
   or unrelated repositories just to combine searches.
2. Call `rlm` with `path` and self-contained Python `code`. `ctx` is a string for
   a file or a dictionary of relative paths to text for a directory. Each call
   starts a fresh process; variables do not persist between calls.
3. Print only the evidence needed for the question, with paths or line numbers
   where useful. The source stays outside the conversation unless printed;
   context usage still depends on the output and the number of calls.
4. Inspect the `[RLM load]` report. If `partial` is true, check relevant skipped
   sources explicitly before concluding that something does not exist.
5. Reuse findings. Follow-up reads of identified passages are appropriate; a
   successful RLM call does not prohibit ordinary focused inspection.

When another tool returns a saved artifact path, analyze the artifact instead
of asking for the full output inline. For a file above the loader limit, create
a narrowly filtered artifact using bounded/streaming extraction first.

## Semantic Subqueries

Use `rlm_subquery` only when delegation is permitted and separate semantic
analysis is useful. Pass `path`, `question`, and optionally `extraction_hint`.
Do not paste the source into the question: that duplicates it in parent history.
Pure searches and counts belong in direct tool calls, not a model subquery.

The subquery requests evidence extraction through RLM and returns the child's
text response. Model selection is `RLM_SUBQUERY_MODEL`, then configured
`small_model`, then the parent's actual model. The selected model must support
the tool workflow. Treat the answer as a synthesis, not proof of complete
coverage; inspect reported limitations and check important claims against the
source. Subsessions are not a security sandbox.

## Limits

- Directory loading: 2 MiB per file, 24 MiB total, 4096 loaded files, and 20000
  visited entries. Single-file loading: 24 MiB.
- Generated directories (`.git`, `node_modules`, `.cache`, `.local`, `result`,
  `dist`, `build`), binary/special files, and encountered symlinks are skipped.
  Explicitly selected symlink paths are followed, including Nix store links.
- Execution stops after 30 seconds, cancellation, or 100000 bytes of combined
  stdout/stderr. A stopped or failed call is not a complete analysis.
- These safeguards bound loading and output, not arbitrary Python allocations
  or filesystem access. RLM executes local code with the user's permissions.

## Examples

- Find a filename: use `glob`, then read the relevant small passage directly.
- Find a symbol's definition: use targeted `grep`; read the matching definition.
- Compare error handling across a known API directory: use `rlm` to extract
  matching handlers with paths, then inspect the relevant differences.
- Summarize changes around errors in a large log: use `rlm` to extract bounded
  error windows. If semantic delegation is useful and allowed, pass the log or
  a filtered artifact path to `rlm_subquery` with a specific question.
- After a partial repository scan, verify a claim of absence with focused
  searches of relevant skipped sources instead of treating ctx as exhaustive.
