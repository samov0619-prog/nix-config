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
    this.editor.replaceText(this.draft);
  }

  canSend() {
    const body = this.draft.toLowerCase();
    return !this.words.some((word) => body.includes(word.toLowerCase()));
  }

  historyView(channel, message, revealed = false) {
    if (channel === "mail") {
      return { text: message.text, concealed: false };
    }
    return {
      text: message.text,
      concealed: message.status === "rejected" && !revealed,
    };
  }
}
