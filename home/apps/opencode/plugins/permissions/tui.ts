import { Plugin } from "@opencode/plugin/tui";
import { basename } from "node:path";
import { permissionList } from "./state.ts";

const directory = (api: Plugin.Context) => {
  const route = api.ui.router.current();
  // Never fall back to the launch project while a viewed session hydrates.
  if (route.type === "session")
    return api.data.session.get(route.sessionID)?.location.directory;
  return api.location?.directory || api.data.location.default().directory;
};
const project = (api: Plugin.Context) => {
  const route = api.ui.router.current();
  return route.type === "session"
    ? api.data.session.get(route.sessionID)?.projectID
    : undefined;
};
export const display = (value: string) =>
  value.replace(
    /[\u0000-\u001f\u007f-\u009f\u2028-\u202e\u2066-\u2069]/g,
    (character) =>
      `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`,
  );

export default Plugin.define({
  id: "local.permissions",
  setup(api) {
    let disposed = false;
    let running = false;
    let cancel: (() => void) | undefined;
    api.keymap.layer(() => ({
      mode: "global",
      commands: [
        {
          id: "local.permissions.open",
          title: "Manage saved permissions for this project",
          palette: true,
          slash: { name: "permissions" },
          run: async () => {
            if (disposed || running) return;
            running = true;
            const cwd = directory(api);
            let model: ReturnType<typeof permissionList> | undefined;
            try {
              if (!cwd) throw new Error("Session location is not loaded");
              const info = await api.client.location.get({
                location: { directory: cwd },
              });
              const current = () =>
                !disposed &&
                directory(api) === cwd &&
                (!project(api) || project(api) === info.project.id);
              if (!info.project?.id) throw new Error("No project identity");
              if (!current()) return;
              model = permissionList({
                projectID: info.project.id,
                current,
                list: (projectID) =>
                  api.client.permission.saved.list({ projectID }),
                remove: (id) => api.client.permission.saved.remove({ id }),
                confirm: (entry) =>
                  api.ui.dialog.confirm({
                    title: "Remove saved permission?",
                    message: `${display(entry.action)} · ${display(entry.resource)}\n\nRemove this saved Always for ${display(cwd)}? Configured rules stay unchanged.`,
                    label: { confirm: "Remove", cancel: "Cancel" },
                  }),
              });
              cancel = () => model?.dispose();
              await model.load();
              if (!current()) return;
              if (model.view.error) {
                api.ui.toast.show({
                  message: model.view.error,
                  variant: "error",
                });
                return;
              }
              let requested: string | undefined;
              let choosing = true;
              const selected = await api.ui.dialog.select({
                title: `Saved permissions for ${display(basename(cwd) || cwd)}`,
                placeholder: model.view.entries.length
                  ? "Search saved Always"
                  : "No saved permissions for this project",
                options: model.view.entries.map((entry) => ({
                  title: display(entry.resource),
                  category: display(entry.action),
                  value: entry.id,
                })),
                actions: [
                  {
                    bind: "ctrl+d",
                    title: "delete",
                    onTrigger: (id: string) => {
                      if (!choosing || disposed) return;
                      choosing = false;
                      if (current()) requested = id;
                      // Actions do not settle select(). Close our own list first;
                      // its promise resumes only after native clear() completes.
                      api.ui.dialog.clear();
                    },
                  },
                  {
                    bind: "q",
                    title: "close",
                    selection: "none",
                    onTrigger: () => {
                      if (!choosing || disposed) return;
                      choosing = false;
                      api.ui.dialog.clear();
                    },
                  },
                ],
              });
              choosing = false;
              if (!current()) return;
              const id = requested ?? selected;
              if (id === undefined) return; // Esc, q or another native dialog.
              const removed = await model.erase(id);
              if (!current()) return;
              if (model.view.error)
                api.ui.toast.show({
                  message: model.view.error,
                  variant: "error",
                });
              else if (removed)
                api.ui.toast.show({
                  message: "Saved permission removed",
                  variant: "success",
                });
            } catch {
              if (!disposed)
                api.ui.toast.show({
                  message:
                    "Saved-permissions operation failed. Reopen the list to check its current state.",
                  variant: "error",
                });
            } finally {
              model?.dispose();
              cancel = undefined;
              running = false;
            }
          },
        },
      ],
    }));
    return () => {
      disposed = true;
      cancel?.();
      // Promise-based dialogs have no public ownership handle. Invalidate the
      // operation, never clear a possibly newer dialog during plugin cleanup.
    };
  },
});
