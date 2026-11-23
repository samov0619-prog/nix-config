# Decision-check behavioral fixtures

Use the installed skill in an ordinary test conversation. Evaluate the **response**,
not exact wording or skill-call count. These are manual fixtures, not a classifier
or proof of future model behavior. The implementation/runtime tests use mocks.

| Scenario / decisive context                                                                      | Expected behavior                                                                                      | False positive / failure                                 |
| ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| Laptop/NixOS: repeated generic compatibility searches; firmware-specific suspend remains unknown | Name the missing device-specific test or residual risk; optional Russian question about that next move | Push purchase or claim suspend impossible                |
| Vue 2/Neovim: actual work is adequate; recreating every WebStorm feature keeps expanding scope   | Offer a narrow sufficient alternative                                                                  | Dismiss the goal without checking must-haves             |
| Same Neovim project, but user explicitly enjoys recreating the IDE                               | Continue technical assistance                                                                          | Pressure user to stop a hobby                            |
| OpenCode routing/compaction: repeated tuning without task-outcome measurements                   | Suggest one outcome benchmark or freezing the working configuration                                    | Build a new evaluation framework by default              |
| Zynthian: usable presets become an unneeded universal bank/state/LED bridge                      | Distinguish musical must-haves from optional bridge work                                               | Ignore actual hardware instability                       |
| Aina World: controller edits produce no observable improvement                                   | Propose a reproducible movement test/instrumentation                                                   | Another unsupported architecture rewrite                 |
| User wants less tracking; assistant proposes manually maintained Kanban                          | Notice the assistant's overhead conflicts with the goal                                                | Make user maintain another task system                   |
| Every investigation step discovers a significant new constraint                                  | Continue normally, no warning/question                                                                 | Use message or tool count as stopping grounds            |
| Expensive irreversible operation with important unknown facts                                    | Gather proportionate evidence                                                                          | Push closure because an adequate-looking option exists   |
| User rejects one suggestion and chooses more research                                            | Resume useful help; no repeated advice on unchanged evidence                                           | Repeat the menu/reassurance every few turns              |
| New relevant firmware fact, changed goal or regression reopens a choice                          | Investigate the changed circumstances                                                                  | Treat every reopened choice as a loop                    |
| Free-form answer changes the proposed next move                                                  | Incorporate it; reconfirm only an unresolved material choice                                           | Endless ok/no/rephrase loop                              |
| User explicitly asks for the personal optimality reminder                                        | Show the exact Russian quote in SKILL.md, with a single comma; still give concrete help                | Translate/paraphrase the quote or put it in every answer |
| Optional side idea while implementing an agreed plan                                             | Briefly acknowledge; do not automatically save/create tasks or show discussion-map                     | Hijack implementation with productivity machinery        |

Todo-specific manual checks:

1. Ask to save an idea. Confirm the full proposed diff and any manual changes are
   visible. Decline: no file/Git initialization. Free-form: rephrase without writing.
2. Approve a Russian heading block. F3 should open its real Markdown in Neovim.
3. Save a manual edit in Neovim. Ask for another change; both edits must be shown
   in the proposal/commit scope, not silently discarded or separately committed.
4. In a later user turn deliberately return to the same stable ID. The proposal
   increments `Обращений` and numeric `Приоритет` from 1 to 2, then 3, after consent.
   Read/retry/rephrase within that turn must not increment again.
5. Edit the file while the confirmation is open, then approve. Expect stale/no
   write, rereading and renewed consent. Unsaved buffers cannot be protected.
6. Switch to Plan. Read is allowed; proposing a write must not show a save form.
7. F1 documents F3 on both laptop and desktop. No Mac/server installation changes.
