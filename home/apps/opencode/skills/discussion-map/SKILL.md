---
name: discussion-map
description: Use when two or more established, independent discussion threads need state tracking, or the user explicitly requests a discussion map. Do not load merely for multiple steps or turns, a routine status check, or a topic change.
---

# Discussion Map

Keep a compact map of established discussion threads when their separate states
need coordination. This is a lightweight response convention, not a persistent
task database.

## When to Use

- Two or more independent threads are already active or deliberately deferred,
  and a map would help keep their decisions and next actions separate.
- The user explicitly asks for a discussion map, even for a single thread.

Do not infer multiple threads from the implementation steps of one task. A first
question, ordinary follow-up, generic progress request, or change of subject is
not sufficient by itself. Do not load this skill in anticipation of a discussion
that might become multi-threaded later.

## Map Format

Use short sections in the user's language, corresponding to:

- `Active`: active thread and its immediate goal.
- `Planned`: agreed next work not yet started.
- `Deferred`: deliberately deferred thread and why.
- `Resolved`: decision or completed result worth retaining.

Use short meaningful headings and one concise summary per item. Do not assign
permanent numbers or render a large table by default. The user may refer to a
previous topic by a number if one was used locally, but numbering is optional.

Show the map briefly only when it clarifies the qualifying threads or the user
explicitly requests it. Omit empty sections. Otherwise continue naturally and
preserve the relevant state in the response itself; do not repeat a map on every
turn just because this skill is loaded.

## Topic Changes

Do not create or recommend a new chat for a small branch, clarification, or
related follow-up. Keep it in the current discussion and update the map when
useful.

A topic change alone is not a reason to load this skill or show a map. Suggest a
new chat only when the user explicitly wants to separate a new, unrelated topic
from the active work; do not treat a normal follow-up as such a request.

OpenCode cannot create a TUI session. When a new chat is appropriate, keep the
current work running and provide a short handoff in this chat:

- goal of the new topic;
- important decisions already made;
- open questions;
- relevant paths and commands.

Then invite the user to open a new chat. Do not end or abandon the current
work automatically.
