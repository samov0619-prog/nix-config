export class Composer {
  constructor(editor) {
    this.editor = editor;
    this.draft = "";
    this.words = [];
  }

  receive(event) {
    if (event.status !== "rejected") return;
    this.draft = event.text;
    this.words = event.words ?? [];
    const caret = this.editor.focused ? this.editor.getCaret() : null;
    this.editor.replaceText(this.draft);
    if (caret !== null) {
      this.editor.setCaret(Math.min(caret, this.draft.length));
    }
  }

  canSend() {
    const body = this.draft.toLowerCase();
    return !this.words.some((word) => body.includes(word.toLowerCase()));
  }

  historyView(channel, message, revealed = false) {
    return {
      text: message.text,
      concealed: message.status === "rejected" && !revealed,
    };
  }
}
