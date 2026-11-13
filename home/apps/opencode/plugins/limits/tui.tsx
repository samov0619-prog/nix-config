import { Plugin } from "@opencode/plugin/tui";
import { createSignal, Show } from "solid-js";
import { checkpointKey, checkpointRequest, windowLabel } from "./policy.ts";
import { Limits } from "./rpc.ts";

export default Plugin.define({
  id: "local.limits.ui",
  setup(api) {
    const rpc = api.client.rpc(Limits);
    const [status, setStatus] = createSignal<any>();
    const [now, setNow] = createSignal(Date.now());
    let disposed = false;
    let pending: Promise<void> | undefined;
    let again = false;
    const location = () => api.location ?? api.data.location.default();
    const sync = () => {
      if (disposed) return Promise.resolve();
      if (pending) {
        again = true;
        return pending;
      }
      pending = rpc
        .status({}, { location: location() })
        .then((value) => {
          if (!disposed) setStatus(value);
        })
        .catch(() => {
          if (!disposed) setStatus(undefined);
        })
        .finally(() => {
          pending = undefined;
          if (again && !disposed) {
            again = false;
            void sync();
          }
        });
      return pending;
    };
    // Use the host's reconnecting stream, not rpc.events.on's one-shot
    // subscription, which ends permanently on a transport disconnect in 2.1.4.
    const stop = api.data.on("rpc.local.limits.updated", () => {
      void sync();
    });
    void sync();
    // A local minute clock only: no provider/server polling while idle.
    const clock = setInterval(() => setNow(Date.now()), 60_000);
    clock.unref?.();

    const sessionID = () => {
      const route = api.ui.router.current();
      return route.type === "session" ? route.sessionID : undefined;
    };
    const syncCheckpoint = () => {
      const id = sessionID();
      if (!id || disposed) return;
      api.data.session.invalidate(id);
      void api.data.session.sync(id).catch(() => {});
    };
    const stopMetadata = api.data.on("session.metadata.updated", (event) => {
      if (event.data.sessionID === sessionID()) syncCheckpoint();
    });
    const stopConnected = api.data.on("server.connected", () => {
      // Events missed while disconnected are not replayed. Re-read both states
      // once after reconnect, without introducing idle polling.
      void sync();
      syncCheckpoint();
    });
    const ready = () => {
      const id = sessionID();
      return (
        id &&
        (api.data.session.get(id)?.metadata?.[checkpointKey] as any)?.ready ===
          true
      );
    };
    const resetTime = (value: number) => {
      const minutes = Math.max(0, Math.ceil((value * 1000 - now()) / 60_000));
      return minutes >= 60
        ? `${Math.floor(minutes / 60)}h${minutes % 60}m`
        : `${minutes}m`;
    };
    const text = () => {
      const value = status();
      const snapshot = value?.snapshot;
      const age = snapshot
        ? Math.max(0, Math.floor((now() - snapshot.observedAt) / 60_000))
        : 0;
      return `${age >= 2 ? ` (as of ${age}m ago)` : ""} | Active: ${value?.active ?? "?"}`;
    };
    const Status = () => (
      <box flexDirection="row" flexWrap="wrap" gap={1}>
        <text fg={api.theme.text.muted}>
          {status()?.reason === "token-sharing-quota-unavailable"
            ? "Limits: "
            : "Limits left: "}
          {status()?.snapshot?.windows?.length
            ? status().snapshot.windows.map((item: any, index: number) => (
                <span>
                  {index ? " · " : ""}
                  {`${windowLabel(item.seconds)} ${Math.round(item.remaining)}% `}
                  <Show
                    when={
                      status()?.windowModes?.[item.key] === "warn" ||
                      status()?.windowModes?.[item.key] === "wrap"
                    }
                  >
                    <span
                      style={{
                        fg:
                          status()?.windowModes?.[item.key] === "wrap"
                            ? "#e5c07b"
                            : api.theme.text.muted,
                      }}
                    >
                      {"⚠ "}
                    </span>
                  </Show>
                  {`↻${resetTime(item.resetAt)}`}
                </span>
              ))
            : status()?.reason === "token-sharing-quota-unavailable"
              ? "not exposed by token sharing"
              : "unavailable"}
          {text()} | Checkpoint
        </text>
        <Show
          when={ready()}
          fallback={
            <text fg={api.theme.text.feedback.info.muted ?? "#607f9f"}>+</text>
          }
        >
          <text
            fg={
              api.theme.text.feedback.success.muted ??
              api.theme.text.feedback.success.base
            }
          >
            ✓
          </text>
        </Show>
      </box>
    );
    const slots = [
      api.ui.slot({ append: "home.footer", render: Status }),
      api.ui.slot({ append: "session.composer.top", render: Status }),
    ];
    api.keymap.layer(() => ({
      mode: "global",
      commands: [
        {
          id: "local.checkpoint.prepare",
          title: "Prepare reviewed handoff checkpoint",
          palette: true,
          slash: { name: "checkpoint" },
          run: async () => {
            const id = sessionID();
            if (!id) return;
            await api.client.session.prompt({
              sessionID: id,
              text: checkpointRequest,
            });
          },
        },
        {
          id: "local.checkpoint.reset",
          title: "Mark checkpoint pending",
          palette: true,
          slash: { name: "checkpoint-reset" },
          run: async () => {
            const id = sessionID();
            if (!id) return;
            const session = await api.client.session.get({ sessionID: id });
            await api.client.session.update({
              sessionID: id,
              metadata: {
                ...session.metadata,
                [checkpointKey]: { ready: false },
              },
            });
            api.data.session.invalidate(id);
            await api.data.session.sync(id);
          },
        },
        {
          id: "local.limits.reset",
          title: "Dismiss budget warnings for this cycle",
          palette: true,
          slash: { name: "limits-reset" },
          run: async () => {
            if (
              !(await api.ui.dialog.confirm({
                title: "Dismiss budget warnings?",
                message:
                  "This overrides checkpoint warnings for the current limiting windows. It does NOT restore provider quota. Other computers are not counted. Continue at your own risk?",
                label: { confirm: "Dismiss warnings", cancel: "Cancel" },
              }))
            )
              return;
            const result = (await rpc.reset(
              {},
              { location: location() },
            )) as any;
            api.ui.toast.show({
              message: result.reset
                ? "Budget warnings dismissed; provider quota unchanged"
                : "Budget unavailable; nothing reset",
              variant: "info",
            });
            await sync();
          },
        },
      ],
    }));
    return () => {
      disposed = true;
      clearInterval(clock);
      stop();
      stopMetadata();
      stopConnected();
      slots.forEach((remove) => remove());
    };
  },
});
