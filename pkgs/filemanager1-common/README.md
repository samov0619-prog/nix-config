# FileManager1: local URI authority

The package remains pinned to `900fccc13dc57e45b527b9acace47ea79c0d9c01`.
`localhost-uri.patch` fixes one normalization bug before arguments reach the
existing wrappers: `file://localhost/path` and `file:///path` must refer to the
same local path, as specified by [RFC 8089 §2](https://www.rfc-editor.org/rfc/rfc8089#section-2).
`localhost` is this machine, not a remote host or an HTTP server.

The patch removes only an exact `localhost/` authority, case-insensitively,
after the existing `file://` handling. It preserves the leading slash and leaves
percent decoding to the wrappers, avoiding double decoding. Plain paths and
empty-authority URIs retain their behavior. Other hostnames are **not** rewritten
as localhost; their previous handling is unchanged, not newly validated or made
into a supported remote-filesystem feature. Wrapper quoting, Kitty/Yazi selection,
D-Bus activation, source pin and dependencies are unchanged.

## Checks

```fish
set fm_source (nix eval --raw .#homeConfigurations.samov-laptop.config.services.filemanager1-common.package.src.outPath)
python3 -B pkgs/filemanager1-common/test_localhost_uri.py --source "$fm_source"
nix eval --impure --offline --json --option allow-import-from-derivation false --file pkgs/filemanager1-common/test-declarations.nix
```

The source path must already exist, for example after the user's package/HM build;
evaluation alone does not realize it. The test does not download sources. It needs
Python, `cc`, `patch` and Bash. It copies only the pinned C source and Yazi wrapper
to an isolated temporary directory and applies the actual package patch with
zero fuzz. Two tiny C executables run the **extracted production argument loop**,
before and after the patch, without daemon or D-Bus code. The original control
reproduces the old bug. The patched loop feeds the actual Yazi wrapper with the
existing Nix substitutions and a fake terminal that only captures arguments.

Seven tests cover localhost/empty authority equivalence, hostname case, root and
multiple arguments, percent-encoding preservation, unrelated authorities/paths,
ShowItems/ShowFolders with spaces, Unicode, quotes and literal shell characters,
and Nix patch registration. Five selected HM declarations check GUI-only scope,
the unchanged Kitty/Yazi wrapper and the daemon/activation wiring. This is not a
full package build, compiled-service test, ShowItemProperties check or real
Kitty/Yazi/browser/D-Bus integration test. No user files are opened by these tests.

On a pin update, check whether upstream now normalizes localhost correctly before
removing the patch. A patch conflict alone does not prove that. The old-bug control
is specific to the current pin and must be reviewed alongside an upstream fix.

## Apply and accept

1. After review, the user applies Home Manager: on Acer,
   `home-manager switch --flake .#samov-laptop`; desktop uses `.#samov-desktop`.
   Do not apply the Lenovo draft on Acer. No NixOS rebuild is needed.
2. Ensure the daemon uses the new executable:
   `systemctl --user restart filemanager1-dbus.service`.
3. In Fish, create a harmless fixture and compare both local URI forms:

   ```fish
   set check_dir (mktemp -d /tmp/opencode/yazi-uri-check.XXXXXX)
   touch "$check_dir/test.txt"
   busctl --user call org.freedesktop.FileManager1 /org/freedesktop/FileManager1 org.freedesktop.FileManager1 ShowItems ass 1 "file://$check_dir/test.txt" ""
   busctl --user call org.freedesktop.FileManager1 /org/freedesktop/FileManager1 org.freedesktop.FileManager1 ShowItems ass 1 "file://localhost$check_dir/test.txt" ""
   ```

   Both should open Kitty/Yazi at the same directory with `test.txt` selected.
4. Check the browser's usual “Show in folder” action. This remains separate live
   acceptance; the agent did not build, activate or restart the service.
