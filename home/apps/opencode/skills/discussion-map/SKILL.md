---
name: discussion-map
description: Multi-turn planning or discussion that needs compact tracking of active, planned, deferred, and resolved threads. Use when a conversation has several branches, the user requests status, or the topic clearly changes.
---

# Discussion Map

Keep a compact semantic map of the current discussion when it helps maintain
context. This is a lightweight response convention, not a persistent task
database.

## Map Format

Use these short sections when showing a map:

- `В работе`: active thread and its immediate goal.
- `В плане`: agreed next work not yet started.
- `Отложено`: deliberately deferred thread and why.
- `Решено`: decision or completed result worth retaining.

Use short meaningful headings and one concise summary per item. Do not assign
permanent numbers or render a large table by default. The user may refer to a
previous topic by a number if one was used locally, but numbering is optional.

Show the map briefly only when several active branches exist, the user asks for
status, or there is a clear topic transition. Otherwise continue naturally and
preserve the relevant state in the response itself.

## Topic Changes

Do not create or recommend a new chat for a small branch, clarification, or
related follow-up. Keep it in the current discussion and update the map when
useful.

Suggest a new chat only when the user explicitly says `новая тема`, `отдельный
вопрос`, or `не связано с предыдущим`, or starts a self-contained task that
does not depend on active threads.

OpenCode cannot create a TUI session. When a new chat is appropriate, keep the
current work running and provide a short handoff in this chat:

- goal of the new topic;
- important decisions already made;
- open questions;
- relevant paths and commands.

Then invite the user to open a new chat. Do not end or abandon the current
work automatically.
