# Local onionbell compatibility fixes

The package pins upstream revision `1bd6d6f7527c213452b8da4b3be3074cc0c06841`.
Updating `flake.lock` does not update this revision.

## IPC EOF

In the pinned [upstream reader](https://github.com/onion108/onionbell/blob/1bd6d6f7527c213452b8da4b3be3074cc0c06841/src/app.rs#L143-L173),
`read()` returning zero is ignored. A disconnected IPC socket therefore causes
a busy loop that grows the event buffer. `ipc-eof.patch` changes both reads to
`read_exact()`: EOF becomes `UnexpectedEof`, the process exits with failure,
and the existing `Restart=on-failure` service policy handles reconnection.

The independent `ipc-test-harness.patch` makes the existing reader callable
without constructing audio state and accepts a `Read` implementation.
`ipc-tests.rs` exercises real Unix sockets: complete frames and UTF-8, immediate
EOF, a truncated event, and a truncated UTF-8 character. Its reader guard fails
on a second read after EOF, so the unfixed reader cannot hang or exhaust memory.
Socket reads also have a one-second timeout.

### Updating upstream / removing the fix

1. Update `rev` and its source hash in `default.nix` after reviewing upstream.
   Patches use zero fuzz; a changed reader that rejects a patch is a signal to
   review it, not evidence by itself that the upstream bug is fixed.
2. Keep the EOF tests and test harness, adapting the harness if upstream changes
   the reader API. Build **without `ipc-eof.patch`**, from the repository root:

   ```fish
   nix build --no-link --impure --expr '
     let
       flake = builtins.getFlake (toString ./.);
       pkgs = import flake.inputs.nixpkgs { system = builtins.currentSystem; };
       onionbell = pkgs.callPackage ./pkgs/onionbell { };
     in onionbell.overrideAttrs (old: {
       patches = builtins.filter
         (patch: builtins.baseNameOf patch != "ipc-eof.patch")
         old.patches;
     })
   '
   ```

   The currently pinned upstream fails the three EOF tests immediately.
   Compilation or patch failures do not establish whether the EOF bug is fixed.
3. When the build and all tests pass without the fix, delete `ipc-eof.patch`
   and its entry in `patches`. Retain the regression tests. Keep the Ogg and
   `clients.pseudo` compatibility fixes unless separately verified obsolete.
4. Build the laptop and desktop Home Manager activation packages without
   activation. The user applies the updated package with Home Manager;
   no NixOS rebuild is needed.
