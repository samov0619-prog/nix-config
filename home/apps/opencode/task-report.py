"""Read-only OpenCode task accounting. No source text or prompts in reports."""

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import re


def default_paths():
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return data / "opencode/opencode.db", state / "opencode/task-usage"


def connect(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("BEGIN")  # Consistent snapshot, including WAL, without copying a live DB.
    return db


def recent_sessions(db, limit):
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    sources = []
    if "session_v2" in tables:
        sources.append("SELECT id,parent_id,version,time_updated FROM session_v2")
    if "session" in tables:
        sources.append("SELECT id,parent_id,version,time_updated FROM session" + (
            " WHERE id NOT IN (SELECT id FROM session_v2)" if "session_v2" in tables else ""))
    if not sources:
        raise ValueError("No supported V1/V2 session storage")
    return [dict(row) for row in db.execute(
        " UNION ALL ".join(sources) + " ORDER BY time_updated DESC LIMIT ?", (limit,))]


def load_messages(db, session, v2=False):
    if v2:
        result = []
        for row in db.execute(
                "SELECT id,type,time_created,data FROM session_message WHERE session_id=? ORDER BY seq", (session,)):
            info = json.loads(row["data"])
            kind = row["type"]
            model = info.get("model") or {}
            info.update(role="assistant" if kind == "compaction" else kind,
                        providerID=model.get("providerID", "?"), modelID=model.get("id", "?"),
                        variant=model.get("variant"))
            parts = list(info.get("content", [])) if kind == "assistant" else []
            for part in parts:
                if part.get("type") == "tool":
                    part["tool"] = part.get("name", "?")
                    state = part.get("state") or {}
                    content = state.get("content", [])
                    if content and all(item.get("type") == "text" for item in content):
                        state["output"] = "\n".join(item.get("text", "") for item in content)
            if kind == "compaction":
                info.update(agent="compaction", summary=True, completed=info.get("status") != "running")
                parts.append({"type": "compaction"})
            if info.get("retry"):
                parts.append({"type": "retry"})
            info["_parts"] = parts
            result.append((row["id"], row["time_created"], info))
        return result
    return [(r["id"], r["time_created"], json.loads(r["data"])) for r in db.execute(
        "SELECT id,time_created,data FROM message WHERE session_id=? ORDER BY time_created,id", (session,))]


def load_calls(directory, sessions, start, end, warnings):
    """Merge append-only attempt/response records; never treat them as token samples."""
    calls = {}
    invalid = False
    for sid in sorted(sessions):
        if not re.fullmatch(r"[\w-]{1,128}", sid, flags=re.ASCII):
            continue
        path = Path(directory) / f"{sid}.jsonl"
        try:
            with path.open() as stream:
                for line in stream:
                    try:
                        row = json.loads(line)
                        if row.get("version") != 1 or row.get("sessionID") != sid:
                            raise ValueError("Unsupported call record")
                        key = (sid, row["id"])
                        if not isinstance(row["id"], str) or not re.fullmatch(r"[\w-]{1,128}", row["id"], flags=re.ASCII):
                            raise ValueError("Invalid call ID")
                        if row.get("event") == "attempt":
                            if not isinstance(row.get("time"), (int, float)):
                                raise ValueError("Invalid timestamp")
                            if not start <= row["time"] < end:
                                continue
                            # Allowlist even when reading an externally modified journal.
                            call = {k: row[k] for k in ("id", "sessionID", "time")}
                            for field in ("kind", "agent", "providerID", "modelID", "variant", "wireModel", "effort", "transport"):
                                value = row.get(field)
                                if isinstance(value, str) and re.fullmatch(r"[\w.:/@+\-]{1,160}", value, flags=re.ASCII):
                                    call[field] = value
                            calls.setdefault(key, call)
                        elif row.get("event") == "response" and key in calls:
                            status = row.get("status")
                            if not isinstance(status, int) or not 100 <= status <= 599:
                                raise ValueError("Invalid HTTP status")
                            calls[key]["http_status"] = status
                        elif row.get("event") != "response":
                            raise ValueError("Unknown call event")
                    except (ValueError, KeyError, TypeError, AttributeError):
                        invalid = True
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError):
            invalid = True
    if invalid:
        warnings.append("Unreadable/unsupported model-call records; call history may be incomplete")
    result = sorted(calls.values(), key=lambda row: (row["time"], row["id"]))
    for call in result:
        status = call.get("http_status")
        call["observation"] = ("http_response_headers" if status is not None else "dispatch_hook_only")
    return result


def report(db, session, usage_dir, turn=None, calls_dir=None):
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    v2 = "session_v2" in tables and db.execute("SELECT 1 FROM session_v2 WHERE id=?", (session,)).fetchone() is not None
    table = "session_v2" if v2 else "session"
    if table not in tables:
        raise ValueError("Session not found in supported V1/V2 storage")
    sessions = {r["id"]: dict(r) for r in db.execute(f"SELECT id,parent_id,time_created FROM {table}")}
    if session not in sessions:
        raise ValueError("Session not found")
    root = load_messages(db, session, v2)
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
        messages = load_messages(db, sid, v2) if sid in sessions else []
        eligible = {mid: m for mid, ts, m in messages if start <= ts < end}
        parts = [(mid, part) for mid, info in eligible.items() for part in info.get("_parts", [])] if v2 else [(row["message_id"], json.loads(row["data"])) for row in db.execute(
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
    calls = load_calls(calls_dir, selected, start, end, warnings) if calls_dir is not None else []
    if not calls:
        warnings.append("No model-call journal for this selection; historical title/generate models cannot be reconstructed from messages")
    warnings.append("Model calls are observed transport attempts since plugin installation, not completed/billed calls; HTTP headers do not prove stream completion")
    warnings.append("Session hooks do not cover out-of-band plugin calls; later hooks may rewrite requests; missing/oversized/unsupported bodies leave wire model/effort unknown")
    warnings.append("Token totals use messages/legacy ledgers only; V2 title usage events and transient generation are not added here")
    warnings.append("Stored variants are labels, not proof of resolved reasoning effort; retry parts do not cover all transport retries")
    warnings.append("Reported cost may be zero/unpriced (e.g. subscription); not an invoice")
    warnings.append("Deleted/unlinked historical sessions and out-of-band model calls cannot be reconstructed")
    return {
        "version": 2, "storage": "v2" if v2 else "v1", "session": session, "turn": turn_id,
        "sessions": sorted(selected), "archived_children": len(records),
        "totals": dict(totals), "root_tokens": dict(root_totals),
        "by_model": {k: dict(v) for k, v in by_model.items()},
        "by_route": {k: dict(v) for k, v in by_route.items()},
        "model_calls": calls, "observed_model_attempts": len(calls),
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
    parser.add_argument("--calls-dir", type=Path, default=default_usage.parent / "model-calls")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session")
    group.add_argument("--recent", type=int, metavar="N")
    parser.add_argument("--turn", help="User message ID or last; defaults to the whole session")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        with closing(connect(args.db)) as db:
            if args.recent is not None:
                if args.recent < 1 or args.turn:
                    raise ValueError("--recent requires N > 0 and cannot be used with --turn")
                result = recent_sessions(db, args.recent)
            else:
                result = report(db, args.session, args.usage_dir, args.turn, args.calls_dir)
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
    print(f'Model calls ({result["observed_model_attempts"]} observed transport attempts; not token samples):')
    for call in result["model_calls"]:
        model = f'{call.get("providerID", "?")}/{call.get("modelID", "?")}'
        timestamp = datetime.fromtimestamp(call["time"] / 1000, timezone.utc).isoformat(timespec="milliseconds")
        print(f'  {timestamp} {call["sessionID"]} {call.get("kind", "?")}/{call.get("agent", "?")} '
              f'{model} variant={call.get("variant", "default/unknown")} '
              f'wire={call.get("wireModel", "?")} effort={call.get("effort", "?")} '
              f'{call.get("transport", "?")} status={call.get("http_status", "unknown")} {call["observation"]}')
    print(f'Compaction requests: {result["compactions"]}; summaries: {result["summary_messages"]}; '
          f'retry parts: {result["retry_parts"]}; failed messages: {result["failed_messages"]}')
    print("Tools: calls / errors / stored output chars / exact repeat chars")
    for name, stat in sorted(result["tools"].items()):
        print(f'  {name}: {stat["calls"]} / {stat.get("errors", 0)} / {stat.get("stored_output_chars", 0)} / {stat.get("exact_repeat_chars", 0)}')
    for warning in result["warnings"]:
        print(f"NOTE: {warning}")


if __name__ == "__main__":
    main()
