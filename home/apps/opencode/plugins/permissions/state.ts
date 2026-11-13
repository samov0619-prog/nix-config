export type SavedPermission = {
  id: string;
  projectID: string;
  action: string;
  resource: string;
};

export type PermissionView = {
  entries: SavedPermission[];
  selected: number;
  armed?: string;
  busy: boolean;
  error: string;
};

// The dialog owns only saved Always grants, never configured policy or the DB.
export function permissionList(options: {
  projectID: string;
  current: () => boolean;
  list: (projectID: string) => Promise<SavedPermission[]>;
  remove: (id: string) => Promise<void>;
  changed: (view: PermissionView) => void;
  close: () => void;
}) {
  let alive = true;
  let state: PermissionView = {
    entries: [],
    selected: 0,
    busy: false,
    error: "",
  };
  const valid = () => {
    if (!alive) return false;
    if (options.current()) return true;
    alive = false;
    options.close();
    return false;
  };
  const publish = () => {
    if (valid()) options.changed({ ...state });
  };
  const rows = async () =>
    (await options.list(options.projectID))
      // Defense in depth: never show or delete another project's grant even if
      // an adapter accidentally returns an unfiltered response.
      .filter((entry) => entry.projectID === options.projectID)
      .map((entry) => ({ ...entry }))
      .sort(
        (a, b) =>
          a.action.localeCompare(b.action) ||
          a.resource.localeCompare(b.resource) ||
          a.id.localeCompare(b.id),
      );
  const replace = (entries: SavedPermission[], id?: string) => {
    const index = entries.findIndex((entry) => entry.id === id);
    state = {
      ...state,
      entries,
      selected:
        index >= 0
          ? index
          : Math.min(state.selected, Math.max(0, entries.length - 1)),
    };
  };
  return {
    get view() {
      return state;
    },
    async load() {
      if (!valid() || state.busy) return;
      state = { ...state, busy: true, armed: undefined, error: "" };
      publish();
      try {
        const entries = await rows();
        if (!valid()) return;
        replace(entries);
      } catch {
        if (!valid()) return;
        state = {
          ...state,
          error: "Could not load permissions. Close and reopen to retry.",
        };
      } finally {
        state = { ...state, busy: false };
        publish();
      }
    },
    move(delta: number) {
      if (!valid() || state.busy) return;
      state = {
        ...state,
        armed: undefined,
        error: "",
        selected: Math.max(
          0,
          Math.min(state.entries.length - 1, state.selected + delta),
        ),
      };
      publish();
    },
    disarm() {
      if (!valid()) return;
      state = { ...state, armed: undefined };
      publish();
    },
    async erase() {
      if (!valid() || state.busy) return;
      const selected = state.entries[state.selected];
      if (!selected) return;
      if (state.armed !== selected.id) {
        state = { ...state, armed: selected.id, error: "" };
        publish();
        return;
      }
      state = { ...state, armed: undefined, busy: true, error: "" };
      publish();
      try {
        // A grant may have changed in another client since it was displayed.
        const fresh = await rows();
        if (!valid()) return;
        const candidate = fresh.find((entry) => entry.id === selected.id);
        if (
          !candidate ||
          candidate.action !== selected.action ||
          candidate.resource !== selected.resource
        ) {
          replace(fresh, selected.id);
          state = {
            ...state,
            error:
              "Permission changed or disappeared. Confirm again if needed.",
          };
          return;
        }
        await options.remove(selected.id);
        if (!valid()) return;
        replace(fresh.filter((entry) => entry.id !== selected.id));
        try {
          const entries = await rows();
          if (valid()) replace(entries, state.entries[state.selected]?.id);
        } catch {
          state = {
            ...state,
            error: "Deleted; refresh failed. Close and reopen to retry.",
          };
        }
      } catch {
        if (!valid()) return;
        state = {
          ...state,
          error: "Deletion failed. Close and reopen to check the saved grant.",
        };
      } finally {
        state = { ...state, busy: false };
        publish();
      }
    },
    dispose() {
      alive = false;
    },
  };
}
