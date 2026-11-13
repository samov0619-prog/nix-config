import { Plugin } from "@opencode/plugin/tui";
import { useTerminalDimensions } from "@opentui/solid";
import type { ScrollBoxRenderable } from "@opentui/core";
import { createEffect, createSignal, For, onCleanup, Show } from "solid-js";
import { permissionList, type PermissionView } from "./state.ts";

const directory = (api: Plugin.Context) => {
  const route = api.ui.router.current();
  // Do not fall back to a different project while the viewed session hydrates.
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
// Render control characters as text, not terminal commands or extra list rows.
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
    let opening = false;
    let active: { close: () => void } | undefined;
    api.keymap.layer(() => ({
      mode: "global",
      commands: [
        {
          id: "local.permissions.open",
          title: "Manage saved permissions for this project",
          palette: true,
          slash: { name: "permissions" },
          run: async () => {
            if (disposed || opening || active) return;
            opening = true;
            const cwd = directory(api);
            try {
              if (!cwd) throw new Error("Session location is not loaded");
              const info = await api.client.location.get({
                location: { directory: cwd },
              });
              if (disposed || directory(api) !== cwd) return;
              if (!info.project?.id) throw new Error("No project identity");
              const current = () =>
                directory(api) === cwd &&
                (!project(api) || project(api) === info.project.id);
              if (!current()) throw new Error("Project identity changed");
              let closed = false;
              const dialog = {
                close: () => {
                  if (!closed && active === dialog) api.ui.dialog.clear();
                },
              };
              active = dialog;
              api.ui.dialog.show(
                () => (
                  <PermissionDialog
                    api={api}
                    projectID={info.project.id}
                    cwd={cwd}
                    current={() => !closed && !disposed && current()}
                    close={dialog.close}
                  />
                ),
                () => {
                  closed = true;
                  if (active === dialog) active = undefined;
                },
              );
              api.ui.dialog.set({ size: "large", centered: true });
            } catch {
              active?.close();
              if (!disposed)
                api.ui.toast.show({
                  message:
                    "Could not resolve this project. No permissions changed.",
                  variant: "error",
                });
            } finally {
              opening = false;
            }
          },
        },
      ],
    }));
    return () => {
      disposed = true;
      active?.close();
    };
  },
});

function PermissionDialog(props: {
  api: Plugin.Context;
  projectID: string;
  cwd: string;
  current: () => boolean;
  close: () => void;
}) {
  const { api } = props;
  const dimensions = useTerminalDimensions();
  const [view, setView] = createSignal<PermissionView>({
    entries: [],
    selected: 0,
    busy: false,
    error: "",
  });
  let details: ScrollBoxRenderable | undefined;
  const model = permissionList({
    projectID: props.projectID,
    current: props.current,
    list: (projectID) => api.client.permission.saved.list({ projectID }),
    remove: (id) => api.client.permission.saved.remove({ id }),
    changed: setView,
    close: props.close,
  });
  onCleanup(() => model.dispose());
  createEffect(() => {
    if (!props.current()) props.close();
  });
  void model.load();
  const count = () =>
    Math.max(1, Math.min(12, Math.floor((dimensions().height - 14) / 2)));
  const start = () =>
    Math.max(
      0,
      Math.min(
        view().selected - Math.floor(count() / 2),
        view().entries.length - count(),
      ),
    );
  const selected = () => view().entries[view().selected];
  const move = (delta: number) => {
    model.move(delta);
    details?.scrollTo(0);
  };
  api.keymap.layer(() => ({
    mode: "modal",
    priority: 20,
    commands: [
      { bind: "up", run: () => move(-1) },
      { bind: "down", run: () => move(1) },
      { bind: "ctrl+d", run: () => model.erase() },
      { bind: "q", run: props.close },
      { bind: "escape", run: props.close },
      {
        bind: "pageup",
        run: () => {
          model.disarm();
          details?.scrollBy(-3);
        },
      },
      {
        bind: "pagedown",
        run: () => {
          model.disarm();
          details?.scrollBy(3);
        },
      },
    ],
  }));
  return (
    <box padding={1}>
      <text fg={api.theme.text.base}>Saved permissions</text>
      <text fg={api.theme.text.muted} wrapMode="none" height={1}>
        {display(props.cwd)}
      </text>
      <text fg={api.theme.text.muted}>
        Saved Always only · configuration is unchanged
      </text>
      <Show
        when={view().entries.length}
        fallback={
          <text>
            {view().busy
              ? "Loading…"
              : view().error
                ? "List unavailable"
                : "No saved permissions for this project"}
          </text>
        }
      >
        <For each={view().entries.slice(start(), start() + count())}>
          {(entry, index) => (
            <text
              height={1}
              wrapMode="none"
              fg={
                start() + index() === view().selected
                  ? api.theme.text.base
                  : api.theme.text.muted
              }
            >
              {`${start() + index() === view().selected ? "›" : " "} ${display(entry.action)} · ${display(entry.resource)}`}
            </text>
          )}
        </For>
        <text
          fg={api.theme.text.muted}
        >{`${view().selected + 1}/${view().entries.length} · ${display(selected()?.id ?? "")}`}</text>
        <scrollbox
          ref={(value) => {
            details = value;
          }}
          height={Math.max(2, Math.min(6, dimensions().height - 22))}
        >
          <text wrapMode="word">
            {selected()
              ? `${display(selected()!.action)} · ${display(selected()!.resource)}`
              : ""}
          </text>
        </scrollbox>
      </Show>
      <text fg={api.theme.text.muted}>
        {view().busy
          ? "Working…"
          : view().armed
            ? "Press Ctrl+D again to delete this saved grant"
            : "↑/↓ select · Ctrl+D twice delete · q/Esc close"}
      </text>
      <Show when={view().error}>
        <text fg={api.theme.text.base}>{view().error}</text>
      </Show>
      <text fg={api.theme.text.muted}>
        PgUp/PgDn details · deletion does not change configured rules
      </text>
    </box>
  );
}
