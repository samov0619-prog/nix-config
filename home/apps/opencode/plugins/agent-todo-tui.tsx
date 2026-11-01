import { Plugin } from "@opencode/plugin/tui";
import { useTerminalDimensions } from "@opentui/solid";
import type { ScrollBoxRenderable, TextareaRenderable } from "@opentui/core";
import {
  createEffect,
  createSignal,
  For,
  onCleanup,
  Show,
  untrack,
} from "solid-js";
import {
  readReview,
  SUBMIT,
  type ReviewDescriptor,
} from "./agent-todo-review.ts";

export default Plugin.define({
  id: "local.agent-todo-review",
  setup(context) {
    const [memory, updateMemory] = context.storage.memory("review-dismissals", {
      initial: { ids: [] as string[] },
    });
    return context.ui.slot({
      append: "app",
      render() {
        const dimensions = useTerminalDimensions();
        const [covered, setCovered] = createSignal<string>();
        let active: { id: string; close: () => void } | undefined;
        createEffect(() => {
          const route = context.ui.router.current();
          const sessionID =
            route.type === "session" ? route.sessionID : undefined;
          const location =
            (sessionID && context.data.session.get(sessionID)?.location) ||
            context.location ||
            context.data.location.default();
          const form = sessionID
            ? context.data.session.form.list(sessionID, location)?.[0]
            : undefined;
          if (covered() && covered() !== form?.id) setCovered(undefined);
          if (active && active.id !== form?.id) untrack(() => active?.close());
          if (!form || active || memory.ids.includes(form.id)) return;
          const review = readReview(form);
          const tool = form.metadata?.tool as
            { messageID?: string; id?: string } | undefined;
          if (!review || !tool?.messageID || !tool.id) return;
          const message = context.data.session.message.get(
            form.sessionID,
            tool.messageID,
          );
          if (
            message?.type !== "assistant" ||
            !message.content.some(
              (part) =>
                part.type === "tool" &&
                part.id === tool.id &&
                part.name === "agent_todo_propose" &&
                part.state.status === "running",
            )
          )
            return;
          untrack(() => {
            let finished = false;
            const dismiss = () => {
              if (finished) return;
              finished = true;
              active = undefined;
              updateMemory((draft) => {
                draft.ids = [...draft.ids.slice(-99), form.id];
              });
              // Escape, backdrop, replacement, route change and plugin disposal
              // all cancel, never reply. Already-completed forms need no action.
              if (
                context.data.session.form
                  .list(form.sessionID, location)
                  ?.some((item) => item.id === form.id)
              )
                void context.data.session.form
                  .cancel(
                    { sessionID: form.sessionID, formID: form.id },
                    location,
                  )
                  .catch((error) => {
                    // Recover the ordinary UI if cancellation could not reach
                    // the server; the stock form still cannot grant Submit.
                    if (covered() === form.id) setCovered(undefined);
                    context.ui.toast.show({
                      message: String(error),
                      variant: "error",
                    });
                  });
            };
            const close = () => {
              context.ui.dialog.clear();
              dismiss();
            };
            const reply = async (answer: Record<string, string>) => {
              if (finished) return;
              await context.data.session.form.reply(
                { sessionID: form.sessionID, formID: form.id, answer },
                location,
              );
              if (finished) return;
              finished = true;
              active = undefined;
              context.ui.dialog.clear();
            };
            active = { id: form.id, close };
            setCovered(form.id);
            context.ui.dialog.show(
              () => (
                <TodoDialog
                  context={context}
                  review={review}
                  texts={form.fields
                    .slice(0, -1)
                    .map((field) => field.description ?? "")}
                  reply={reply}
                />
              ),
              dismiss,
            );
            context.ui.dialog.set({ size: "xlarge", centered: true });
          });
        });
        onCleanup(() => active?.close());
        // The public dialog backdrop is translucent and does not suppress the
        // native Questions composer. Cover it without mutating the host tree or
        // form cache. Keep covering until cancellation/reply removes the form,
        // so dismissing the dialog does not briefly reveal a second prompt.
        return (
          <Show when={covered()}>
            <box
              position="absolute"
              left={0}
              top={0}
              width={dimensions().width}
              height={dimensions().height}
              zIndex={2999}
              backgroundColor={context.theme.background.base}
            />
          </Show>
        );
      },
    });
  },
});

function TodoDialog(props: {
  context: Plugin.Context;
  review: ReviewDescriptor;
  texts: string[];
  reply: (answer: Record<string, string>) => Promise<void>;
}) {
  const { context, review } = props;
  const dimensions = useTerminalDimensions();
  const [tab, setTab] = createSignal(0);
  const [feedback, setFeedback] = createSignal<Record<string, string>>({});
  const [editing, setEditing] = createSignal(false);
  const [choice, setChoice] = createSignal(0);
  const [busy, setBusy] = createSignal(false);
  const [error, setError] = createSignal("");
  let scroll: ScrollBoxRenderable | undefined;
  let editor: TextareaRenderable | undefined;
  const final = () => tab() === review.notes.length;
  const compact = () =>
    review.notes.reduce((width, _, i) => width + String(i + 1).length + 3, 10) >
    dimensions().width - 8;
  const key = () => `q${tab()}`;
  const stash = () => {
    if (editing() && editor && !editor.isDestroyed)
      setFeedback({ ...feedback(), [key()]: editor.plainText });
  };
  const move = (direction: number) => {
    if (busy()) return;
    stash();
    setEditing(false);
    setTab(
      (value) =>
        (value + direction + review.notes.length + 1) %
        (review.notes.length + 1),
    );
    scroll?.scrollTo(0);
  };
  const edit = () => {
    if (!busy()) setEditing(true);
  };
  const send = async (action: string) => {
    if (busy()) return;
    stash();
    setBusy(true);
    setError("");
    try {
      const answer = Object.fromEntries(
        Object.entries(feedback()).filter(([, value]) => value.trim()),
      );
      answer[`q${review.notes.length}`] = action;
      await props.reply(answer);
    } catch (error) {
      setError(String(error));
      setBusy(false);
    }
  };
  const confirm = () => {
    if (editing()) {
      stash();
      setEditing(false);
      if (final()) setChoice(0);
      return;
    }
    if (!final()) {
      move(1);
      return;
    }
    if (choice() === 2) {
      edit();
      return;
    }
    void send(
      choice() === 1
        ? "Reject"
        : feedback()[key()]?.trim() || SUBMIT + review.token,
    );
  };
  context.keymap.layer(() => ({
    mode: "modal",
    priority: 20,
    enabled: !busy(),
    commands: [
      { bind: "left", enabled: !editing(), run: () => move(-1) },
      { bind: "right", enabled: !editing(), run: () => move(1) },
      { bind: "tab", run: () => move(1) },
      { bind: "shift+tab", run: () => move(-1) },
      {
        bind: "up",
        enabled: !editing(),
        run: () => {
          if (final()) setChoice((i) => (i + 2) % 3);
          else scroll?.scrollBy(-1);
        },
      },
      {
        bind: "down",
        enabled: !editing(),
        run: () => {
          if (final()) setChoice((i) => (i + 1) % 3);
          else scroll?.scrollBy(1);
        },
      },
      { bind: "home", enabled: !editing(), run: () => scroll?.scrollTo(0) },
      {
        bind: "end",
        enabled: !editing(),
        run: () => scroll?.scrollTo(Infinity),
      },
      { bind: "ctrl+up", enabled: !editing(), run: () => scroll?.scrollBy(-1) },
      {
        bind: "ctrl+down",
        enabled: !editing(),
        run: () => scroll?.scrollBy(1),
      },
      { bind: "a", enabled: !editing(), run: edit },
      { bind: "return", enabled: !editing(), run: confirm },
    ],
  }));
  const muted = context.theme.text.muted;
  const base = context.theme.text.base;
  return (
    <box padding={1} gap={1}>
      <box flexDirection="row" gap={1} flexShrink={0}>
        <Show
          when={!compact()}
          fallback={
            <text fg={base}>
              {final()
                ? "Submit"
                : `Note ${tab() + 1} of ${review.notes.length}`}
            </text>
          }
        >
          <For each={[...review.notes.map((_, i) => String(i + 1)), "Submit"]}>
            {(label, i) => (
              <text
                fg={i() === tab() ? base : muted}
                onMouseUp={() => move(i() - tab())}
              >
                {i() === tab() ? `[${label}]` : label}
              </text>
            )}
          </For>
        </Show>
      </box>
      <scrollbox
        ref={(value: ScrollBoxRenderable) => {
          scroll = value;
        }}
        height={Math.max(
          2,
          dimensions().height - (editing() ? 18 : final() ? 16 : 13),
        )}
        flexShrink={1}
        minHeight={2}
      >
        <text fg={base} wrapMode="word">
          {final() ? review.summary : props.texts[tab()]}
        </text>
      </scrollbox>
      <Show
        when={editing()}
        fallback={
          <>
            <Show when={feedback()[key()]}>
              <text fg={muted}>
                Comment saved for {final() ? "batch" : "this note"} (a to edit).
              </text>
            </Show>
            <Show
              when={final()}
              fallback={
                <text fg={muted} onMouseUp={edit}>
                  a · Type your own answer (this note only)
                </text>
              }
            >
              <For each={["Submit", "Reject", "Type your own answer"]}>
                {(label, i) => (
                  <text
                    fg={choice() === i() ? base : muted}
                    onMouseUp={() => {
                      setChoice(i());
                      confirm();
                    }}
                  >
                    {choice() === i() ? "› " : "  "}
                    {label}
                  </text>
                )}
              </For>
              <Show
                when={Object.values(feedback()).some((text) => text.trim())}
              >
                <text fg={muted}>
                  Comments request revision; nothing will be saved.
                </text>
              </Show>
            </Show>
          </>
        }
      >
        <text fg={muted}>
          {final() ? "Batch feedback" : "Feedback for this note only"}
        </text>
        <textarea
          ref={(value: TextareaRenderable) => {
            editor = value;
          }}
          focused
          initialValue={feedback()[key()] ?? ""}
          minHeight={1}
          maxHeight={3}
          textColor={base}
          focusedTextColor={base}
          cursorColor={base}
          keyBindings={[{ name: "return", action: "submit" }]}
          onSubmit={() => {
            stash();
            setEditing(false);
            if (final()) setChoice(0);
          }}
        />
      </Show>
      <Show when={error()}>
        <text fg={base}>{error()}</text>
      </Show>
      <text fg={muted} flexShrink={0}>
        ⇆ tab ↑↓ {final() ? "select" : "scroll"} enter confirm esc dismiss
      </text>
    </box>
  );
}
