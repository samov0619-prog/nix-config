// Execute path/journal functions from the pinned source; no live data or SQLite.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import path from "node:path";
import { test } from "node:test";

const source =
  process.env.OPENCODE_TEST_SOURCE ??
  execFileSync(
    "nix",
    [
      "eval",
      "--offline",
      "--no-write-lock-file",
      "--no-update-lock-file",
      "--impure",
      "--raw",
      "--expr",
      '(builtins.getFlake "/home/samov/nix-config").inputs.opencode.outPath',
    ],
    { encoding: "utf8", timeout: 20000 },
  ).trim();
const read = (name) => readFileSync(path.join(source, name), "utf8");
const plain = (text) =>
  stripTypeScriptTypes(text)
    .replace(/^import .*\n/gm, "")
    .replaceAll("export ", "");

test("native XDG roots apply on both home-style and Mac-style homes", () => {
  const code = plain(read("packages/util/src/global-roots.ts"));
  for (const home of ["/home/user", "/Users/user"]) {
    const roots = new Function(
      "process",
      "os",
      "path",
      `${code}\nreturn roots;`,
    )({ env: {} }, { homedir: () => home, tmpdir: () => "/tmp" }, path);
    assert.equal(roots("opencode").data, `${home}/.local/share/opencode`);
    assert.equal(roots("opencode").state, `${home}/.local/state/opencode`);
  }
  const roots = new Function("process", "os", "path", `${code}\nreturn roots;`)(
    {
      env: {
        XDG_DATA_HOME: "/data",
        XDG_STATE_HOME: "/state",
        XDG_CONFIG_HOME: "/config",
        XDG_CACHE_HOME: "/cache",
      },
    },
    { homedir: () => "/Users/user", tmpdir: () => "/tmp" },
    path,
  );
  assert.deepEqual(roots("opencode"), {
    data: "/data/opencode",
    state: "/state/opencode",
    config: "/config/opencode",
    cache: "/cache/opencode",
    tmp: "/tmp/opencode",
  });
});

test("native database namespace and explicit override resolution", () => {
  const code = plain(read("packages/cli/src/database-path.ts"));
  const db = (channel, env = {}) =>
    new Function(
      "process",
      "path",
      "OPENCODE_CHANNEL",
      `${code}\nreturn databasePath('/data/opencode');`,
    )({ env }, path, channel);
  for (const channel of ["prod", "latest", "dev", "beta", "next"])
    assert.equal(db(channel), "/data/opencode/opencode.db");
  assert.equal(db("local"), "/data/opencode/opencode-local.db");
  assert.equal(
    db("local", { OPENCODE_DISABLE_CHANNEL_DB: "true" }),
    "/data/opencode/opencode.db",
  );
  assert.equal(
    db("prod", { OPENCODE_DB: "custom.db" }),
    "/data/opencode/custom.db",
  );
  assert.equal(
    db("prod", { OPENCODE_DB: "/private/session.db" }),
    "/private/session.db",
  );
  assert.equal(db("prod", { OPENCODE_DB: ":memory:" }), ":memory:");
});

test("prod keeps a distinct service/TUI namespace, not a distinct default DB", () => {
  const code = read("packages/cli/src/services/service-config.ts");
  const start = code.indexOf("export function filename(");
  const end = code.indexOf("export function defaultPort(", start);
  assert.ok(start > 0 && end > start);
  const filename = new Function(
    "OPENCODE_CHANNEL",
    `${plain(code.slice(start, end))}\nreturn filename;`,
  )("prod");
  assert.equal(filename(), "service-prod.json");
  for (const channel of ["latest", "dev", "beta", "next"])
    assert.equal(filename(channel), "service.json");
  assert.match(code, /configFile: path\.join\(global\.config, name\)/);
  assert.match(code, /const file = path\.join\(global\.state, name\)/);
  const storage = read("packages/tui/src/context/storage.tsx");
  assert.match(storage, /path\.join\(root, segment\(channel\), "tui"\)/);
  assert.match(
    read("packages/util/src/global.ts"),
    /config: process\.env\.OPENCODE_CONFIG_DIR \?\? Path\.config/,
  );
});

function run(iterator) {
  let step;
  do {
    step = iterator.next();
  } while (!step.done);
  return step.value;
}
function result(value) {
  const iterator = (function* () {
    return value;
  })();
  iterator.pipe = (...operations) =>
    operations.reduce((input, operation) => operation(input), iterator);
  return iterator;
}

test("actual migration journal skips completed IDs, applies new IDs transactionally, and offers no downgrade", () => {
  const code = read("packages/core/src/database/migration.ts");
  const start = code.indexOf("export function applyOnly(");
  assert.ok(start > 0);
  const applied = [],
    transactions = [],
    statements = [];
  const sql = Object.assign(
    (strings, ...values) => ({ text: strings.join("?"), values }),
    { identifier: (value) => value },
  );
  const db = {
    run: (statement) => {
      statements.push(statement);
      return result();
    },
    all: () =>
      result([
        { id: "already-completed" },
        { id: "future-id-unknown-to-old-binary" },
      ]),
    transaction: (fn) => {
      transactions.push(true);
      return fn(db);
    },
  };
  const Effect = {
    gen: (fn) => {
      const iterator = fn();
      iterator.pipe = (...operations) =>
        operations.reduce((input, operation) => operation(input), iterator);
      return iterator;
    },
    logInfo: () => result(),
    tapError: () => (effect) => effect,
  };
  const apply = new Function(
    "Effect",
    "sql",
    "supportsForeignKeyToggle",
    "EffectDrizzleSqlite",
    `${plain(code.slice(start))}\nreturn applyOnly;`,
  )(Effect, sql, true, {});
  run(
    apply(
      db,
      ["already-completed", "new-id"].map((id) => ({
        id,
        up: () => {
          applied.push(id);
          return result();
        },
      })),
    ),
  );
  assert.deepEqual(applied, ["new-id"]);
  assert.equal(transactions.length, 1);
  assert.equal(
    statements.filter((value) => value.text.includes("INSERT INTO")).length,
    1,
  );
  assert.doesNotMatch(code, /\bdown\s*[:(]/);
  assert.match(
    read(
      "packages/core/src/database/migration/20261025154125_drop_session_pending.ts",
    ),
    /DROP TABLE IF EXISTS.*session_pending/,
  );
});

test("forward message compatibility does not imply that 2.1.4 can read new part rows", () => {
  const history = read("packages/core/src/session/history.ts");
  assert.match(history, /yield\* withParts\(db, rows\)/);
  assert.match(history, /SessionLegacy\.message\(row\.type, row\.data\)/);
  assert.match(
    read("packages/core/src/session/projector.ts"),
    /function partRowWrites\(/,
  );
  const ids = [
    ...read("packages/core/src/database/migration.gen.ts").matchAll(
      /import m\d+ from "\.\/migration\/(.+)\.js"/g,
    ),
  ].map((value) => value[1]);
  assert.equal(
    ids.length,
    64,
    "review migration inventory when changing the pin",
  );
  assert.equal(ids[49], "20261010180456_project_time_archived");
  assert.equal(ids.at(-1), "20261120004954_machine-key");
});
