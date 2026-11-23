---
description: Verify requested browser behavior against requirements with traceable evidence
subagent: false
---

Verify `$ARGUMENTS` in the browser. If arguments are empty, use the browser test
already agreed in this conversation. If no target or scenario is established,
ask for it before interacting with a browser.

## Boundary

- Stay in the current conversation with its existing agent and model. Respect
  applicable project instructions, permissions and Plan restrictions. This command
  is not permission to bypass a read-only mode or start a separate agent.
- This is live verification, not the passive `/delegated-review-chrome` audit.
  If the request is only to assess recorded evidence, follow that workflow instead;
  do not drive the browser or repeat the test.
- Use the existing Chrome MCP when available. Discover actual permitted tools;
  do not invent method names, install/enable a server or add Playwright. The test
  procedure is tool-independent; do not assume browser isolation or a fresh profile.
- Limit interaction to the requested scenario and its agreed data/environment.
  Confirm consequential actions not already authorized: production mutations,
  destructive operations, sending messages, payments or changes to shared data.
  Do not modify code, build, deploy, restart services, commit or publish results.
- Do not close, navigate or modify unrelated tabs, browser profiles, processes or
  data. Use a dedicated test tab when permitted; create and remove test data only
  within the agreed scope. Do not treat tool availability as operational approval.

## Verification

1. Establish the target URL/environment, scenario and expected behavior from
   requirements or an agreed contract, not solely from current implementation.
   Identify needed accounts, data and permissions without exposing credentials.
   If access, browser tools or the application are unavailable, report what is
   blocked rather than substituting invented results or enabling integrations.
2. Identify the tested application/build and relevant source state when available,
   including uncommitted changes. Record how they relate, or state that the link
   is unverified. A local source revision does not prove what a remote app runs;
   do not require a clean checkout or create a commit just to label the test.
   Distinguish live services from mocks, fixtures, cached or intercepted responses.
3. Define a small set of scenarios before interacting: preconditions, actions and
   expected results. Cover the reported bug or primary acceptance path and the
   nearest relevant regression/error/state transitions. Do not expand into a full
   site audit merely because more pages are accessible.
4. Run the authorized scenarios using actual available tools. Observe UI results
   and relevant network/console evidence; compare responses to the applicable
   contract. Keep baseline noise separate from new signals. A screenshot alone
   does not establish backend correctness, and an HTTP error alone does not prove
   which component caused it.
5. Record what actually happened for each scenario, including partial or blocked
   runs. For intermittent behavior, retain attempts and conditions; a few successful
   repetitions do not disprove the bug. Do not infer a root cause from correlation
   or call a regression fixed without observing the required behavior.
6. Keep only necessary, sanitized evidence with enough context to reproduce the
   finding. Exclude tokens, cookies, credentials and unrelated personal/customer
   data from screenshots, traces and reports. Do not export raw evidence or create
   report files without a separate request and an approved destination.
7. Restore only changes created by this test when safe and authorized. Report
   retained test tabs/data or incomplete cleanup; do not broadly clean the session.

## Result

Lead with the outcome: requirements verified, deviations observed, or verification
incomplete. Report:

- Target, application/source identity and any unverified relationship or mocks.
- For each material scenario: preconditions/actions, expected result, actual result,
  status (passed/failed/blocked/not run) and supporting evidence references.
- Relevant network/console findings, reproduction details and coverage limitations.
- Any required follow-up and retained test state. Keep proposed diagnoses separate
  from observations; do not silently fix defects during verification.

Do not claim broader acceptance than the completed scenarios support. If no live
test ran, say so explicitly; a written test plan is not a successful browser run.
