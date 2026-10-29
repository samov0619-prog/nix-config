// A server event stream is shared by all TUI clients. Only the session on this
// client's route (and its descendants) may request sound or terminal attention.
// Do not use directory/project/global-tab membership as an ownership signal.
type Scope = {
	ui: { router: { current(): { type: string; sessionID?: string } } };
	data: { session: { get(id: string): { parentID?: string } | undefined } };
};

export function sessionAttention(context: Scope, sessionID: string | undefined): boolean {
	const route = context.ui.router.current();
	if (route.type !== "session" || !route.sessionID || !sessionID) return false;
	const seen = new Set<string>();
	while (sessionID && !seen.has(sessionID)) {
		if (sessionID === route.sessionID) return true;
		seen.add(sessionID);
		sessionID = context.data.session.get(sessionID)?.parentID;
	}
	// Missing ancestry and malformed cycles fail closed; never guess ownership.
	return false;
}
