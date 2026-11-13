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
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};
const tick = () => new Promise((resolve) => setImmediate(resolve));
function fixture(entries = [grant("a"), grant("b")]) {
  const state = {
    entries,
    removed: [],
    requests: [],
    views: [],
    current: true,
    closed: 0,
    list: async () => state.entries,
    remove: async (id) => {
      state.entries = state.entries.filter((row) => row.id !== id);
    },
  };
  const model = permissionList({
    projectID: "project-a",
    current: () => state.current,
    close: () => {
      state.closed++;
    },
    changed: (value) => state.views.push(value),
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

test("project-filtered, sorted copies; empty list and selection boundaries", async () => {
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
  state.entries[2].resource = "changed behind the view";
  assert.equal(model.view.entries[0].resource, "command a");
  model.move(-1);
  assert.equal(model.view.selected, 0);
  model.move(100);
  assert.equal(model.view.selected, 1);
  state.entries = [];
  await model.load();
  model.move(1);
  await model.erase();
  assert.equal(model.view.selected, 0);
  assert.deepEqual(state.removed, []);
  assert.equal(model.view.armed, undefined);
});

test("two confirmations delete exactly the selected ID; navigation and details disarm", async () => {
  const { model, state } = fixture();
  await model.load();
  await model.erase();
  assert.equal(model.view.armed, "a");
  assert.deepEqual(state.removed, []);
  model.move(-1); // Even a clamped move cancels confirmation.
  assert.equal(model.view.armed, undefined);
  await model.erase();
  model.disarm();
  assert.equal(model.view.armed, undefined);
  model.move(1);
  await model.erase();
  assert.equal(model.view.armed, "b");
  await model.erase();
  assert.deepEqual(state.removed, ["b"]);
  assert.deepEqual(
    model.view.entries.map((row) => row.id),
    ["a"],
  );
  assert.equal(model.view.selected, 0);
  assert.equal(model.view.busy, false);
  assert.equal(model.view.armed, undefined);
  assert.equal(
    state.requests.length,
    3,
    "initial, pre-delete validation, refresh",
  );
});

for (const change of ["action", "resource", "projectID", "disappeared"]) {
  test(`stale ${change} refuses deletion and requires new confirmation`, async () => {
    const { model, state } = fixture();
    await model.load();
    await model.erase();
    if (change === "disappeared") state.entries.shift();
    else state.entries[0][change] = "different";
    await model.erase();
    assert.deepEqual(state.removed, []);
    assert.equal(model.view.armed, undefined);
    assert.match(model.view.error, /changed or disappeared/);
    assert.equal(model.view.busy, false);
    await model.erase();
    assert.deepEqual(
      state.removed,
      [],
      "fresh selection is armed, not immediately deleted",
    );
  });
}

test("serializes loading, validation, deletion and refresh; no duplicate requests", async () => {
  const { model, state } = fixture();
  let wait = deferred();
  state.list = () => wait.promise;
  const loading = model.load();
  await model.load();
  await model.erase();
  model.move(1);
  assert.equal(state.requests.length, 1);
  wait.resolve(state.entries);
  await loading;
  await model.erase();
  wait = deferred();
  const deleting = model.erase();
  await model.erase();
  await model.load();
  model.move(1);
  assert.equal(model.view.selected, 0);
  assert.equal(state.requests.length, 2);
  const removing = deferred();
  state.remove = () => removing.promise;
  wait.resolve(state.entries);
  await tick();
  await model.erase();
  assert.deepEqual(state.removed, ["a"]);
  const refreshing = deferred();
  state.list = () => refreshing.promise;
  removing.resolve();
  await tick();
  await model.erase();
  assert.deepEqual(state.removed, ["a"]);
  refreshing.resolve([grant("b")]);
  await deleting;
  assert.equal(model.view.busy, false);
});

test("loading, validation and deletion errors never silently remove a row", async () => {
  const { model, state } = fixture();
  state.list = async () => {
    throw new Error("private server message");
  };
  await model.load();
  assert.match(model.view.error, /Could not load/);
  assert.doesNotMatch(model.view.error, /private/);
  assert.equal(model.view.busy, false);
  state.list = async () => state.entries;
  await model.load();
  await model.erase();
  state.list = async () => {
    throw new Error("offline");
  };
  await model.erase();
  assert.deepEqual(state.removed, []);
  assert.match(model.view.error, /Deletion failed/);
  assert.equal(model.view.armed, undefined);
  state.list = async () => state.entries;
  state.remove = async () => {
    throw new Error("offline");
  };
  await model.erase();
  await model.erase();
  assert.equal(model.view.entries.length, 2);
  assert.match(model.view.error, /Deletion failed/);
  assert.equal(model.view.busy, false);
});

test("successful delete plus failed refresh is reported distinctly", async () => {
  const { model, state } = fixture();
  await model.load();
  state.remove = async () => {
    state.list = async () => {
      throw new Error("offline");
    };
  };
  await model.erase();
  await model.erase();
  assert.deepEqual(
    model.view.entries.map((row) => row.id),
    ["b"],
  );
  assert.match(model.view.error, /Deleted; refresh failed/);
  assert.equal(model.view.busy, false);
});

for (const stop of ["dispose", "scope-change"]) {
  test(`${stop} during loading or validation prevents deletion and late publication`, async () => {
    for (const phase of ["loading", "validation"]) {
      const { model, state } = fixture();
      if (phase === "validation") {
        await model.load();
        await model.erase();
      }
      const wait = deferred();
      state.list = () => wait.promise;
      const operation = phase === "loading" ? model.load() : model.erase();
      const publications = state.views.length;
      if (stop === "dispose") model.dispose();
      else state.current = false;
      wait.resolve(state.entries);
      await operation;
      await model.erase();
      model.move(1);
      model.disarm();
      assert.deepEqual(state.removed, []);
      assert.equal(state.views.length, publications);
      assert.equal(state.closed, stop === "dispose" ? 0 : 1);
    }
  });
}

test("closing after DELETE dispatch cannot undo it but never refreshes or publishes", async () => {
  const { model, state } = fixture();
  await model.load();
  await model.erase();
  const wait = deferred();
  state.remove = () => wait.promise;
  const operation = model.erase();
  await tick();
  assert.deepEqual(state.removed, ["a"]);
  const publications = state.views.length;
  model.dispose();
  wait.resolve();
  await operation;
  assert.equal(state.views.length, publications);
  assert.equal(state.requests.length, 2);
});
