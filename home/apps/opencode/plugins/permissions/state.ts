export type SavedPermission = {
  id: string;
  projectID: string;
  action: string;
  resource: string;
};

export type PermissionView = {
  entries: SavedPermission[];
  busy: boolean;
  error: string;
};

// The dialog owns only saved Always grants, never configured policy or the DB.
export function permissionList(options: {
  projectID: string;
  current: () => boolean;
  list: (projectID: string) => Promise<SavedPermission[]>;
  remove: (id: string) => Promise<void>;
  confirm: (entry: SavedPermission) => Promise<boolean | undefined>;
}) {
  let alive = true;
  let state: PermissionView = {
    entries: [],
    busy: false,
    error: "",
  };
  const valid = () => {
    if (!alive) return false;
    if (options.current()) return true;
    alive = false;
    return false;
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
  const replace = (entries: SavedPermission[]) => {
    state = { ...state, entries };
  };
  return {
    get view() {
      return state;
    },
    async load() {
      if (!valid() || state.busy) return;
      state = { ...state, busy: true, error: "" };
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
      }
    },
    async erase(id: string) {
      if (!valid() || state.busy) return false;
      const entry = state.entries.find((entry) => entry.id === id);
      if (!entry) return false;
      const selected = { ...entry };
      state = { ...state, busy: true, error: "" };
      try {
        // Only the native confirmation's explicit true authorizes deletion.
        const confirmed = await options.confirm({ ...selected });
        if (!valid() || confirmed !== true) return false;
        // A grant may have changed in another client since it was displayed.
        const fresh = await rows();
        if (!valid()) return false;
        const candidate = fresh.find((entry) => entry.id === selected.id);
        if (
          !candidate ||
          candidate.action !== selected.action ||
          candidate.resource !== selected.resource
        ) {
          replace(fresh);
          state = {
            ...state,
            error:
              "Permission changed or disappeared. Reopen the list to check it.",
          };
          return false;
        }
        await options.remove(selected.id);
        if (!valid()) return true;
        replace(fresh.filter((entry) => entry.id !== selected.id));
        try {
          const entries = await rows();
          if (valid()) replace(entries);
        } catch {
          state = {
            ...state,
            error: "Deleted; refresh failed. Close and reopen to retry.",
          };
        }
        return true;
      } catch {
        if (!valid()) return false;
        state = {
          ...state,
          error: "Deletion failed. Close and reopen to check the saved grant.",
        };
        return false;
      } finally {
        state = { ...state, busy: false };
      }
    },
    dispose() {
      alive = false;
    },
  };
}
