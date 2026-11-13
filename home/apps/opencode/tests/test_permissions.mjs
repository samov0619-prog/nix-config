import assert from "node:assert/strict";
import { test } from "node:test";
import { permissionList } from "../plugins/permissions/state.ts";

const grant = (id, resource = `command ${id}`, projectID = "project-a") => ({
  id,
  projectID,
  action: "shell",
  resource,
});
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
};
const tick = () => new Promise((resolve) => setImmediate(resolve));
function fixture(entries = [grant("a"), grant("b")]) {
  const state = {
    entries,
    removed: [],
    requests: [],
    confirmations: [],
    current: true,
    list: async () => state.entries,
    confirm: async () => true,
    remove: async (id) => {
      state.entries = state.entries.filter((row) => row.id !== id);
    },
  };
  const model = permissionList({
    projectID: "project-a",
    current: () => state.current,
    confirm: async (entry) => {
      state.confirmations.push(entry);
      return state.confirm(entry);
    },
    list: async (projectID) => {
      state.requests.push(projectID);
      return state.list();
    },
    remove: async (id) => {
      state.removed.push(id);
      return state.remove(id);
    },
  });
  return { model, state };
}

test("project-filtered sorted copies; empty/unknown IDs cannot request confirmation", async () => {
  const { model, state } = fixture([
    grant("b"),
    grant("foreign", "x", "project-b"),
    grant("a"),
  ]);
  await model.load();
  assert.deepEqual(
    model.view.entries.map((row) => row.id),
    ["a", "b"],
  );
  assert.deepEqual(state.requests, ["project-a"]);
  state.entries[2].resource = "external change";
  assert.equal(model.view.entries[0].resource, "command a");
  assert.equal(await model.erase("foreign"), false);
  assert.equal(await model.erase("unknown"), false);
  state.entries = [];
  await model.load();
  assert.equal(await model.erase("a"), false);
  assert.deepEqual(state.confirmations, []);
  assert.deepEqual(state.removed, []);
});

test("native confirmation receives the displayed grant; explicit true deletes only that ID", async () => {
  const { model, state } = fixture();
  await model.load();
  assert.equal(await model.erase("b"), true);
  assert.deepEqual(state.confirmations, [grant("b")]);
  assert.deepEqual(state.removed, ["b"]);
  assert.deepEqual(
    model.view.entries.map((row) => row.id),
    ["a"],
  );
  assert.equal(model.view.busy, false);
  assert.equal(
    state.requests.length,
    3,
    "initial, pre-delete validation, refresh",
  );
});

for (const decision of [false, undefined]) {
  test(`native cancellation ${decision} does not validate or delete`, async () => {
    const { model, state } = fixture();
    state.confirm = async () => decision;
    await model.load();
    assert.equal(await model.erase("a"), false);
    assert.equal(state.confirmations.length, 1);
    assert.equal(state.requests.length, 1);
    assert.deepEqual(state.removed, []);
    assert.equal(model.view.busy, false);
    assert.equal(model.view.error, "");
  });
}

for (const change of ["action", "resource", "projectID", "disappeared"]) {
  test(`stale ${change} after confirmation refuses deletion`, async () => {
    const { model, state } = fixture();
    await model.load();
    state.confirm = async () => {
      if (change === "disappeared") state.entries.shift();
      else state.entries[0][change] = "different";
      return true;
    };
    assert.equal(await model.erase("a"), false);
    assert.deepEqual(state.removed, []);
    assert.match(model.view.error, /changed or disappeared/);
    assert.equal(model.view.busy, false);
  });
}

test("serializes load, confirmation, validation, delete and refresh", async () => {
  const { model, state } = fixture();
  let wait = deferred();
  state.list = () => wait.promise;
  const loading = model.load();
  await model.load();
  await model.erase("a");
  assert.equal(state.requests.length, 1);
  wait.resolve(state.entries);
  await loading;
  const confirmation = deferred();
  state.confirm = () => confirmation.promise;
  const deleting = model.erase("a");
  await model.erase("b");
  await model.load();
  assert.equal(state.confirmations.length, 1);
  assert.equal(state.requests.length, 1);
  wait = deferred();
  confirmation.resolve(true);
  await tick();
  await model.erase("a");
  assert.equal(state.requests.length, 2);
  const removing = deferred();
  state.remove = () => removing.promise;
  wait.resolve(state.entries);
  await tick();
  await model.erase("b");
  assert.deepEqual(state.removed, ["a"]);
  const refreshing = deferred();
  state.list = () => refreshing.promise;
  removing.resolve();
  await tick();
  await model.erase("b");
  assert.deepEqual(state.removed, ["a"]);
  refreshing.resolve([grant("b")]);
  assert.equal(await deleting, true);
  assert.equal(model.view.busy, false);
});

test("load, confirmation, validation and remove errors never silently drop rows", async () => {
  for (const stage of ["load", "confirm", "validate", "remove"]) {
    const { model, state } = fixture();
    const failure = async () => {
      throw new Error("private server message");
    };
    if (stage === "load") state.list = failure;
    await model.load();
    if (stage === "load") assert.match(model.view.error, /Could not load/);
    else {
      if (stage === "confirm") state.confirm = failure;
      if (stage === "validate") state.list = failure;
      if (stage === "remove") state.remove = failure;
      assert.equal(await model.erase("a"), false);
      assert.equal(model.view.entries.length, 2);
      assert.match(model.view.error, /Deletion failed/);
    }
    assert.doesNotMatch(model.view.error, /private/);
    assert.equal(model.view.busy, false);
    assert.equal(state.removed.length, stage === "remove" ? 1 : 0);
  }
});

test("successful delete plus failed refresh is distinct from failed deletion", async () => {
  const { model, state } = fixture();
  await model.load();
  state.remove = async () => {
    state.list = async () => {
      throw new Error("offline");
    };
  };
  assert.equal(await model.erase("a"), true);
  assert.deepEqual(
    model.view.entries.map((row) => row.id),
    ["b"],
  );
  assert.match(model.view.error, /Deleted; refresh failed/);
  assert.equal(model.view.busy, false);
});

for (const stop of ["dispose", "scope-change"]) {
  test(`${stop} during load, confirmation or validation prevents any late delete`, async () => {
    for (const phase of ["loading", "confirmation", "validation"]) {
      const { model, state } = fixture();
      if (phase !== "loading") await model.load();
      const before = model.view.entries;
      const wait = deferred();
      if (phase === "confirmation") state.confirm = () => wait.promise;
      else state.list = () => wait.promise;
      const operation = phase === "loading" ? model.load() : model.erase("a");
      await tick();
      if (stop === "dispose") model.dispose();
      else state.current = false;
      wait.resolve(phase === "confirmation" ? true : state.entries);
      await operation;
      await model.erase("b");
      assert.deepEqual(state.removed, []);
      assert.equal(
        model.view.entries,
        before,
        "late results do not replace the view",
      );
    }
  });
}

test("closing after DELETE dispatch cannot undo it but never refreshes", async () => {
  const { model, state } = fixture();
  await model.load();
  const wait = deferred();
  state.remove = () => wait.promise;
  const operation = model.erase("a");
  await tick();
  assert.deepEqual(state.removed, ["a"]);
  model.dispose();
  wait.resolve();
  await operation;
  assert.equal(state.requests.length, 2);
});
