import { spawn } from "node:child_process";
import { z } from "zod";

// Bounded source loading, not a sandbox: the supplied Python is arbitrary code.
const prelude = String.raw`
import os, re, sys, io, json, stat
from collections import Counter
p = os.path.abspath(os.path.expanduser(sys.argv[1]))
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 24 * 1024 * 1024
MAX_FILES = 4096
MAX_ENTRIES = 20000
EXCLUDED = {'.git', 'node_modules', '.cache', '.local', 'result', 'dist', 'build'}
skipped = Counter()
loaded = entries = 0
ctx = {}
def read_bounded(path, limit):
    # O_NONBLOCK prevents opening a FIFO from hanging before fstat can reject it.
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            skipped['non_regular'] += 1
            return None
        raw = source.read(limit + 1)
    if len(raw) > limit:
        skipped['size_limit'] += 1
        return None
    if b'\0' in raw:
        skipped['binary'] += 1
        return None
    return raw
def visit(directory):
    global loaded, entries
    names = []
    # Bound enumeration itself, before sorting (including very wide directories).
    with os.scandir(directory) as scan:
        for entry in scan:
            entries += 1
            if entries > MAX_ENTRIES:
                skipped['entry_limit'] += 1
                return False
            names.append(entry.name)
    for name in sorted(names):
        if len(ctx) >= MAX_FILES or loaded >= MAX_TOTAL:
            skipped['load_limit'] += 1
            return False
        path = os.path.join(directory, name)
        try:
            if os.path.islink(path):
                skipped['symlink'] += 1
                continue
            if os.path.isdir(path):
                if name in EXCLUDED:
                    skipped['excluded_directory'] += 1
                elif not visit(path):
                    return False
            else:
                raw = read_bounded(path, min(MAX_FILE, MAX_TOTAL - loaded))
                if raw is not None:
                    ctx[os.path.relpath(path, p)] = raw.decode('utf-8', errors='replace')
                    loaded += len(raw)
        except OSError:
            skipped['read_error'] += 1
    return True
try:
    # An explicitly selected symlink is allowed (notably Nix store config links).
    # Links encountered within a directory are skipped; select them directly.
    if os.path.isdir(p):
        visit(p)
    else:
        raw = read_bounded(p, MAX_TOTAL)
        if raw is None:
            raise ValueError('Source rejected; select a regular text file within 24 MiB.')
        loaded = len(raw)
        ctx = raw.decode('utf-8', errors='replace')
finally:
    print('[RLM load] ' + json.dumps({'loaded_bytes': loaded, 'entries': entries,
          'partial': bool(skipped), 'skipped': dict(skipped)}), file=sys.stderr, flush=True)
`;

export default {
	description:
		"Analyze a bounded text source in Python as ctx (string or directory dict). " +
		"Use for large-input content analysis; use glob for filename discovery. " +
		"Directories: 2 MiB/file, 24 MiB total, 4096 files, 20000 entries. " +
		"Generated directories and encountered symlinks are skipped; explicit symlink paths work. " +
		"Always check the load report for partial results. Print only relevant slices.",
	args: {
		path: z.string().describe("Absolute or ~ path to a bounded source"),
		code: z.string().describe("Python code using ctx; print only relevant results"),
	},
	async execute(args: { path: string; code: string }, context?: { abort?: AbortSignal }) {
		if (context?.abort?.aborted) return "[RLM cancelled]";
		return await new Promise<string>((resolve) => {
			const child = spawn("python3", ["-u", "-c", prelude + "\n" + args.code, args.path], {
				stdio: ["ignore", "pipe", "pipe"],
				detached: true,
			});
			const chunks: Buffer[] = [];
			let bytes = 0;
			let reason = "";
			const stop = (message: string) => {
				if (reason) return;
				reason = message;
				// Kill the process group so descendants cannot keep the pipes open.
				try { if (child.pid) process.kill(-child.pid, "SIGKILL"); } catch {}
			};
			const collect = (chunk: Buffer) => {
				const remaining = 100_000 - bytes;
				if (remaining > 0) {
					const kept = Buffer.from(chunk.subarray(0, remaining));
					chunks.push(kept);
					bytes += kept.length;
				}
				if (chunk.length > remaining) stop("output limit exceeded (100000 bytes)");
			};
			child.stdout.on("data", collect);
			child.stderr.on("data", collect);
			const timer = setTimeout(() => stop("timeout (30 seconds)"), 30_000);
			const abort = () => stop("cancelled");
			context?.abort?.addEventListener("abort", abort, { once: true });
			if (context?.abort?.aborted) abort();
			child.on("error", (error) => { reason = `spawn failed: ${error.message}`; });
			child.on("close", (code, signal) => {
				clearTimeout(timer);
				context?.abort?.removeEventListener("abort", abort);
				resolve(Buffer.concat(chunks).toString("utf8") +
					(reason ? `\n[RLM ${reason}]` : code !== 0 ? `\n[RLM exit=${code} signal=${signal}]` : ""));
			});
		});
	},
};
