# Blueman laptop fixes

The existing `blueman-polkit` overlay is selected only by NixOS `laptop` and
`laptop-old`. It enables Polkit build support without changing upstream actions,
wheel authorization, device trust or Bluetooth policy. Desktop/server/Mac are
unchanged. `verify.py` checks the installed constants and exact upstream policies.

## Native notification dialog expiry

The shared GUI preference `notification-daemon = false` keeps pairing and service
authorization in Blueman's native GTK dialogs. In pinned Blueman 2.4.6,
`_NotificationDialog` ignores its `_timeout` argument entirely. ConnectionNotifier
uses this same path for Connected/Disconnected, leaving informational windows open.
Mako's 15-second timeout cannot affect a separate GTK window.

`notification-timeout.patch` adds a GLib timeout to informational native dialogs:

- The default negative timeout means **3 seconds from show**, not construction.
- An explicit positive timeout is honored; explicit zero remains persistent.
- Dialogs with action buttons remain pending until an answer/upstream cancellation.
- Close, response, hide and destroy cancel the timer; repeated show replaces it.
- Expiry hides the informational dialog without invoking a confirmation callback.
- A later battery-text update does not reopen an expired dialog.

This is a local fix/policy, not a claimed upstream backport. No timer service,
Bluetooth reconnect, pairing-key change, driver restart or new notification route
is added. Already running applets/windows keep their old code until restarted.

## Small checks (no build or Bluetooth access)

```fish
python3 -B pkgs/blueman-polkit/tests/test_notification_timeout.py /path/to/blueman-source-or-tarball
nix eval --impure --offline --json --option allow-import-from-derivation false --file pkgs/blueman-polkit/tests/test-declarations.nix
```

The harness applies the exact patch without fuzz/offset in temporary storage,
executes the actual dialog class with mocked GTK/GLib and reproduces the baseline
timeout defect. It is not a native GTK/display/BlueZ integration test. The package's
existing install check also runs the contracts on its patched source, alongside
the unchanged Polkit verifier.

Preparation checks: all eight source-harness scenarios pass on the exact cached
2.4.6 tarball (one reproduces the unpatched defect); the selected four-host Nix
fixture passes. The registered unpatched removal contract correctly fails, so the
checker reports `review-required`, not an upstream-inclusion/removal candidate.
No full package build, activation, native GTK window or real pairing was tested.

The user subsequently applied the 15-second version and confirmed that ordinary
Blueman notifications now close correctly, then requested a 3-second default.
The 3-second revision is source-contract tested, not yet user-applied/accepted.
The agent did not build or activate either version. This report does not establish
all pairing/authorization dialogs, repeated Bluetooth recovery or other hosts.
Only this package override and new patch fingerprints were recorded after source
review; matching inventory bytes are not fresh upstream or live acceptance.

On updates, run the same harness with `--check-upstream` against unpatched source.
Remove the patch only after those contracts pass and live ordinary notices/pairing
remain usable. A patch conflict or version change is not removal evidence. Keep
the scenarios after removal. The fix is registered in `docs/backports/registry.json`.

## User application

1. Review and build/apply the NixOS output: `sudo nixos-rebuild switch --flake .#laptop`
   (use `laptop-old` only on Acer). The agent does not build or activate it.
2. At a convenient session boundary, log out/in to start the updated Blueman
   applet; no Bluetooth daemon restart or deliberate mouse disconnection is needed.
3. On the next naturally occurring Connected/Disconnected notice, check automatic
   closure after about 3 seconds. Existing old windows may need one manual close.
4. During ordinary pairing if needed, confirm that the action dialog stays pending
   and Confirm/Deny work. Do not remove a working mouse merely to run this check.
