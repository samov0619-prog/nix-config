---
name: rlm
description: Large-input tasks — big files, long logs, whole-repository questions — where reading everything into context is wasteful or impossible. Query the input programmatically instead of loading it.
---

# RLM — programmatic / recursive context

When a task needs a large file, many files, or a whole-directory answer:

1. Do **not** read the whole thing with the `read` tool.
2. Use the **`rlm`** tool: pass the `path`; it loads the content as `ctx` in a Python
   REPL (str for a file, `dict{relpath: text}` for a directory). Write `code` that
   greps / regexes / slices / aggregates `ctx` and `print()`s **only** the relevant part.
   Only what you print enters the conversation — token cost stays flat regardless of input size.
   - **Each `rlm` call is a fresh process:** `ctx` is reloaded from `path`, but variables
     from previous calls do **not** persist. Make every `code` block self-contained
     (re-derive anything you need; don't reference names from an earlier call).
   - When another tool reports that its large result was preserved at an artifact path,
     use that path with `rlm`; do not request the full result in the conversation.
3. If a large source needs **semantic** judgement that code can't express, and the
   **`rlm_subquery`** tool is available (recursive variant), pass it the source `path`,
   the question, and optionally an extraction hint. The child session reads the source
   through `rlm` itself; the parent keeps only its final answer.
   - Never put a source fragment into a tool argument. That would copy the fragment into
     the parent session history and defeat the memory boundary.
4. Pull only the resulting slices into context; never the raw bulk.

Prefer `rlm` over `grep`+`read` loops whenever the input is big.

## Examples

- "Which files import `NotificationsStore`?" →
  `rlm(path=".", code="import re\n[print(f) for f,t in ctx.items() if 'NotificationsStore' in t]")`
- "Summarise what changed in this 40k-line log around errors" →
  `rlm_subquery(path="/path/to/log", question="What changed around errors?", extraction_hint="Find error blocks and nearby lines")`.
