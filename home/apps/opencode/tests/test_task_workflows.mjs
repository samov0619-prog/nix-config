// Prompt/source contracts only: not model compliance or live browser acceptance.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const commands = Object.fromEntries(
  ["task-analysis", "browser-verification"].map((name) => [
    name,
    read(`../commands/${name}.md`),
  ]),
);
const analysis = commands["task-analysis"];
const browser = commands["browser-verification"];

test("both workflows are native current-session commands without routing or shell expansion", () => {
  for (const [name, text] of Object.entries(commands)) {
    const match = text.match(
      /^---\ndescription: ([^\n]+)\nsubagent: false\n---\n\n([\s\S]+)$/,
    );
    assert.ok(match, name);
    assert.ok(match[1].length > 20, name);
    assert.equal((match[2].match(/\$ARGUMENTS/g) ?? []).length, 1, name);
    assert.doesNotMatch(text, /!`|^agent:|^model:|^subtask:/m, name);
    assert.match(
      text,
      /current conversation with its existing agent and model/,
      name,
    );
  }
});

test("task analysis stays read-only and uses applicable requirements without imposing a corporate pipeline", () => {
  assert.match(analysis, /read-only analysis, not implementation/);
  assert.match(
    analysis,
    /Do not delegate unless separately requested or required/,
  );
  assert.match(analysis, /Do not create a plan file, task log/);
  assert.match(analysis, /do not impose a corporate tracker requirement/);
  assert.match(
    analysis,
    /Retain source identities, relevant sections and revisions/,
  );
  assert.match(analysis, /do not start implementing/);
  assert.doesNotMatch(analysis, /FBDC-|Kaiten|\.front|MCP-XTRACKER/);
});

test("analysis separates intended and deployed contracts and maps requirements to justified checks", () => {
  assert.match(
    analysis,
    /proposed backend MR contract is not evidence that the deployed API supports/,
  );
  assert.match(
    analysis,
    /requirement → affected area\/change → check and expected result/,
  );
  assert.match(analysis, /independently justified expected result/);
  assert.match(
    analysis,
    /Separate unit\/mock coverage from real integration or browser/,
  );
  assert.match(analysis, /Separate blockers from assumptions/);
});

test("live browser workflow preserves passive-audit, permission and shared-browser boundaries", () => {
  assert.match(browser, /passive `\/delegated-review-chrome` audit/);
  assert.match(browser, /do not drive the browser or repeat the test/);
  assert.match(browser, /existing Chrome MCP/);
  assert.match(browser, /do not assume browser isolation or a fresh profile/);
  assert.match(browser, /Do not close, navigate or modify unrelated tabs/);
  assert.match(browser, /Confirm consequential actions not already authorized/);
  assert.match(
    browser,
    /Do not modify code, build, deploy, restart services, commit or publish results/,
  );
});

test("browser reports real coverage, deployment uncertainty and evidence without leaking private state", () => {
  assert.match(browser, /including uncommitted changes/);
  assert.match(
    browser,
    /A local source revision does not prove what a remote app runs/,
  );
  assert.match(browser, /Distinguish live services from mocks/);
  assert.match(browser, /status \(passed\/failed\/blocked\/not run\)/);
  assert.match(browser, /successful\n   repetitions do not disprove the bug/);
  assert.match(
    browser,
    /Do not export raw evidence or create\n   report files without a separate request/,
  );
  assert.match(browser, /Restore only changes created by this test/);
  assert.match(browser, /If no live\ntest ran, say so explicitly/);
});

test("HM registers workflows through the personal layer, without global command or skill duplicates", () => {
  const module = read("../default.nix");
  const generator = read("../config/personal-layers.nix");
  assert.match(module, /personal-layers\.nix/);
  assert.match(module, /home\.sessionVariables\.OPENCODE_CONFIG/);
  for (const name of Object.keys(commands)) {
    assert.doesNotMatch(
      module,
      new RegExp(`commands/${name}\\.md|skills\\.${name}`),
    );
    const readme = read(`../${name}.README.md`);
    assert.ok(readme.startsWith(`# \`/${name}\``), name);
    assert.ok(generator.includes(name), name);
    assert.match(readme, /HM декларативно подключает слой/, name);
    assert.match(readme, /сборки\/activation и установки на Mac ещё нет/, name);
    assert.match(readme, /только тело без frontmatter/, name);
  }
});
