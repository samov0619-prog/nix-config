"""Read-only OpenCode task accounting. No source text or prompts in reports."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3


def default_paths():
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return data / "opencode/opencode.db", state / "opencode/task-usage"


def connect(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("BEGIN")  # Consistent snapshot, including WAL, without copying a live DB.
    return db


def load_messages(db, session):
    return [(r["id"], r["time_created"], json.loads(r["data"])) for r in db.execute(
        "SELECT id,time_created,data FROM message WHERE session_id=? ORDER BY time_created,id", (session,))]


def report(db, session, usage_dir, turn=None):
    sessions = {r["id"]: dict(r) for r in db.execute("SELECT id,parent_id,time_created FROM session")}
    if session not in sessions:
        raise ValueError("Session not found")
    root = load_messages(db, session)
    if not root:
        raise ValueError("No messages in the supported message/part schema; empty session or unsupported storage version")
    start, end = 0, float("inf")
    turn_id = None
    if turn:
        users = [(mid, ts) for mid, ts, m in root if m.get("role") == "user"]
        if not users:
            raise ValueError("No user messages in session")
        turn_id = users[-1][0] if turn == "last" else turn
        matches = [i for i, (mid, _) in enumerate(users) if mid == turn_id]
        if not matches:
            raise ValueError("User message not found; use --turn last or a user message ID")
        index = matches[0]
        start = users[index][1]
        if index + 1 < len(users):
            end = users[index + 1][1]

    warnings = []
    ledger = []
    for path in sorted(Path(usage_dir).glob("*.json")):
        try:
            row = json.loads(path.read_text())
            if row.get("version") != 1 or not isinstance(row.get("messages"), list):
                raise ValueError("Unknown ledger format")
            ledger.append(row)
        except (OSError, ValueError, AttributeError):
            warnings.append("Unreadable/unsupported usage record; child accounting may be incomplete")

    selected = {session}
    records = {}
    # Follow normal subagent lineage and explicit RLM accounting links.
    while True:
        before = len(selected)
        for sid, row in sessions.items():
            if row["parent_id"] in selected and (not turn or start <= row["time_created"] < end):
                selected.add(sid)
        for row in ledger:
            if row.get("parentSessionID") in selected and (not turn or start <= row["started"] < end):
                selected.add(row["childSessionID"])
                records[row["childSessionID"]] = row
        if len(selected) == before:
            break

    totals = Counter()
    by_model = {}
    by_route = {}
    tools = {}
    seen_outputs = set()
    message_ids = set()
    missing_usage = inflight = compactions = retry_parts = failed_messages = summary_messages = 0
    root_totals = Counter()
    missing_cost = 0

    def account(info, sid, mid, steps=()):
        nonlocal missing_usage, inflight, missing_cost, failed_messages, summary_messages
        key = (sid, mid)
        if key in message_ids:
            return
        message_ids.add(key)
        failed_messages += bool(info.get("error"))
        summary_messages += bool(info.get("summary"))
        if not (info.get("time", {}).get("completed") or info.get("completed")):
            inflight += 1
        # A retried message can contain multiple finished steps. Its tokens field
        # is overwritten, while step-finish parts retain the individual counters.
        samples = list(steps) or [info]
        counts = Counter(assistant_messages=1)
        for sample in samples:
            token = sample.get("tokens")
            if not isinstance(token, dict):
                missing_usage += 1
                continue
            cache = token.get("cache") or {}
            counts.update({
                "input": token.get("input", 0), "cache_read": cache.get("read", 0),
                "cache_write": cache.get("write", 0), "output": token.get("output", 0),
                "reasoning": token.get("reasoning", 0), "recorded_steps": 1,
            })
        if not counts.get("recorded_steps"):
            return
        # Message cost is accumulated by OpenCode; never add both representations.
        counts["cost_reported"] = info.get("cost") or 0
        if info.get("cost") is None:
            missing_cost += 1
        totals.update(counts)
        if sid == session:
            root_totals.update(counts)
        model = f'{info.get("providerID", "?")}/{info.get("modelID", "?")}'
        by_model.setdefault(model, Counter()).update(counts)
        route = f'{info.get("agent", info.get("mode", "?"))}|{model}|{info.get("variant") or "default/unknown"}'
        by_route.setdefault(route, Counter()).update(counts)

    for sid in sorted(selected):
        messages = load_messages(db, sid) if sid in sessions else []
        eligible = {mid: m for mid, ts, m in messages if start <= ts < end}
        parts = [(row["message_id"], json.loads(row["data"])) for row in db.execute(
            "SELECT message_id,data FROM part WHERE session_id=? ORDER BY time_created,id", (sid,)
        ) if row["message_id"] in eligible] if sid in sessions else []
        steps = {}
        for mid, part in parts:
            if part.get("type") == "step-finish":
                steps.setdefault(mid, []).append(part)
        for mid, info in eligible.items():
            if info.get("role") == "assistant":
                account(info, sid, mid, steps.get(mid, ()))
        # Archived counters are a fallback; never count a retained child twice.
        for info in records.get(sid, {}).get("messages", []):
            account(info, sid, info["id"])
        if sid not in sessions:
            continue
        for mid, part in parts:
            kind = part.get("type")
            if kind == "compaction":
                compactions += 1
            if kind == "retry":
                retry_parts += 1
            if kind in ("text", "reasoning") and eligible[mid].get("role") == "assistant":
                totals[f"assistant_{kind}_chars"] += len(part.get("text", ""))
            if kind != "tool":
                continue
            name = part.get("tool", "?")
            stat = tools.setdefault(name, Counter())
            state = part.get("state") or {}
            stat["calls"] += 1
            stat["errors"] += state.get("status") == "error"
            output = state.get("output")
            if isinstance(output, str):
                size = len(output)
                stat["stored_output_chars"] += size
                digest = (name, hashlib.sha256(output.encode()).digest())
                if output and digest in seen_outputs:
                    stat["exact_repeat_chars"] += size
                seen_outputs.add(digest)
            else:
                stat["no_string_output"] += 1

    subqueries = tools.get("rlm_subquery", {}).get("calls", 0)
    unaccounted = max(0, subqueries - len(records))
    if unaccounted:
        warnings.append(f"{unaccounted} RLM calls without linked usage records; totals are incomplete")
    if missing_usage or inflight:
        warnings.append(f"Usage missing for {missing_usage} messages; {inflight} unfinished messages")
    if turn and len(selected) > 1:
        warnings.append("Child attribution for --turn uses start timestamps; use a fresh session per benchmark task")
    if compactions:
        warnings.append("Compaction detected: stored character counts are not a replay of actual model inputs")
    warnings.append("Title and some failed/retried requests have no stored usage; full task accounting requires provider/trace reconciliation")
    warnings.append("Stored variants are labels, not proof of resolved reasoning effort; retry parts do not cover all transport retries")
    warnings.append("Reported cost may be zero/unpriced (e.g. subscription); not an invoice")
    warnings.append("Deleted/unlinked historical sessions and out-of-band model calls cannot be reconstructed")
    return {
        "version": 2, "session": session, "turn": turn_id,
        "sessions": sorted(selected), "archived_children": len(records),
        "totals": dict(totals), "root_tokens": dict(root_totals),
        "by_model": {k: dict(v) for k, v in by_model.items()},
        "by_route": {k: dict(v) for k, v in by_route.items()},
        "processed_input_tokens": sum(totals[k] for k in ("input", "cache_read", "cache_write")),
        "processed_total_tokens": sum(totals[k] for k in ("input", "cache_read", "cache_write", "output", "reasoning")),
        "tools": {k: dict(v) for k, v in tools.items()},
        "unaccounted_rlm_calls": unaccounted, "missing_usage_messages": missing_usage,
        "unfinished_messages": inflight, "missing_cost_messages": missing_cost,
        "compactions": compactions, "summary_messages": summary_messages,
        "retry_parts": retry_parts, "failed_messages": failed_messages,
        "full_task_usage_complete": False, "warnings": warnings,
    }


def main():
    default_db, default_usage = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=default_db)
    parser.add_argument("--usage-dir", type=Path, default=default_usage)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session")
    group.add_argument("--recent", type=int, metavar="N")
    parser.add_argument("--turn", help="User message ID or last; defaults to the whole session")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        with connect(args.db) as db:
            if args.recent is not None:
                if args.recent < 1 or args.turn:
                    raise ValueError("--recent requires N > 0 and cannot be used with --turn")
                result = [dict(row) for row in db.execute(
                    "SELECT id,parent_id,version,time_updated FROM session ORDER BY time_updated DESC LIMIT ?", (args.recent,))]
            else:
                result = report(db, args.session, args.usage_dir, args.turn)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Report unavailable: {error}\n")
    if args.json or args.recent is not None:
        print(json.dumps(result, indent=2))
        return
    print(f'Session: {result["session"]}; turn: {result["turn"] or "all"}; sessions: {len(result["sessions"])}')
    print(f'Processed input (input + cache read + cache write): {result["processed_input_tokens"]:,}')
    print(f'Processed total (including output + reasoning): {result["processed_total_tokens"]:,}')
    for key, value in result["totals"].items():
        print(f"  {key}: {value:,}")
    print("Routes (agent|model|stored variant): processed input / output + reasoning")
    for route, counts in sorted(result["by_route"].items()):
        processed = sum(counts.get(k, 0) for k in ("input", "cache_read", "cache_write"))
        print(f'  {route}: {processed:,} / {counts.get("output", 0) + counts.get("reasoning", 0):,}')
    print(f'Compaction requests: {result["compactions"]}; summaries: {result["summary_messages"]}; '
          f'retry parts: {result["retry_parts"]}; failed messages: {result["failed_messages"]}')
    print("Tools: calls / errors / stored output chars / exact repeat chars")
    for name, stat in sorted(result["tools"].items()):
        print(f'  {name}: {stat["calls"]} / {stat.get("errors", 0)} / {stat.get("stored_output_chars", 0)} / {stat.get("exact_repeat_chars", 0)}')
    for warning in result["warnings"]:
        print(f"NOTE: {warning}")


if __name__ == "__main__":
    main()
