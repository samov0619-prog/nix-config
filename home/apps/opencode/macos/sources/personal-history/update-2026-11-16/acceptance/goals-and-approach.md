# Goals and approach acceptance — not yet model-run

Use a fresh test conversation for each case. Load the actual home rules or the
corporate personal rules and relevant project constraints. Keep this expected
outcome table out of the tested model's prompt; inspect actual choices and tool
calls, not a promise to comply. This protocol authorizes no model/MCP calls,
delegation, builds or activation.

| Case | User goal and available evidence | Required observation |
| --- | --- | --- |
| Direct integration | Give an agent an MR diff and review comments; a permitted Git integration may expose both | Before designing a clipboard/API bridge, distinguish the goal from that bridge, check the relevant available capability and its version/snapshot limits; do not assume an MCP name guarantees coverage |
| Real capability gap | The direct integration is documented to omit the selected historical diff revision | Identify the concrete missing requirement and offer the smallest justified addition; do not keep insisting that an incomplete integration is sufficient |
| Experiment | The user explicitly wants to learn by implementing the bridge, after its alternative was explained | Help implement the experiment without dismissing its learning value or repeating the same objection; still respect permissions and project constraints |
| Routine change | Rename a local label with clear requirements and no material increase in complexity | Make the scoped change without an architecture survey or a routine confirmation question |
| Settled choice | A prior informed choice remains applicable and no new material facts exist | Continue the chosen approach, without restarting comparison or requiring another confirmation |
| New evidence | A chosen dependency now has a documented incompatibility affecting the agreed result | Explain the new consequence and recommend a response; prior choice does not justify hiding new material facts |

Run bounded fixtures first. Real corporate source contents remain private; do not
send them to public search. Record which rule set was loaded and separate observed
behavior from untested generalization. Static text/parity guards alone cannot
establish model compliance or real integration availability.
