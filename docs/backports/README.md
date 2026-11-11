# Backports and temporary fixes

The machine-readable inventory is [registry.json](registry.json). It covers **all
18 active patch files**, their inline companions and temporary package selections.
It distinguishes upstream backports, an unmerged proposed backport, local bug
fixes, packaging compatibility, customizations and test-only instrumentation.

## Inventory

| IDs | Type / scope | Removal evidence |
| --- | --- | --- |
| `btintel-pm` | Two upstream kernel PM backports, Lenovo | Unpatched actual-function/table contracts, then real Bluetooth/Hibernate |
| `pipewire-x11` | Upstream X11 cleanup backport, Lenovo | Unpatched four-case callback contract, then shutdown/audio |
| `nvidia-init-root` | **Unmerged** NVIDIA PR #1512, Lenovo open module only | Unpatched config-open/probe contracts and conftests, then idle/offload/resume |
| `filemanager-localhost`, `filemanager-wrappers` | Local URI bug fix; Nix wrapper compatibility | Unpatched URI/quoting regressions and launcher acceptance |
| `amnezia-routing`, `amnezia-readiness` | Shared client local routing/readiness fixes | Unpatched netlink/Qt/QtRO scenarios, matching GUI/helper, live routing/boot/resume |
| `amnezia-inline-address-dns` | Inline dual-stack IPv4 and empty-DNS fixes | Correct IPv4 assignment/AllowedIPs plus live AWG3.1/DNS |
| `amnezia-packaging-ui`, `amnezia-awg31-selection` | Conan/CMake, paths, metadata, tray/icon/autostart; client/backend pins | Review substitutions independently; official client must satisfy address/routes/backend/PATH and live checks |
| `onionbell-ogg`, `onionbell-eof` | Local Ogg playback and IPC EOF bugs | Real sound/mixer and Unix-socket tests without each fix separately |
| `onionbell-tests`, `onionbell-api` | Test-only patch; inline Rust API compatibility | Keep regressions after fix removal; review API changes separately |
| `onionbell-native-replacement` | Temporary service until native Hyprland bell | Existing libcanberra detection, then native bell acceptance with service stopped |
| `yazi-password`, `yazi-api` | Archive-password bug fix; three API substitutions | Same Lua/7zz regressions without password patch; separate API review and real Yazi acceptance |
| `opencode-routing`, `opencode-attention` | Session/helper/effort migration and attention-policy customizations | Native equivalent satisfies documented runtime/TUI policy, not simply a release bump |
| `opencode-question-location`, `opencode-theme-cache` | Local question and startup-theme bugs | Unpatched real TUI buttons and stale/fresh theme-cache controls |
| `waybar-profile-tooltip` | Lenovo tooltip/cycle customization | Equivalent native feature, helper regressions and live tooltip/click acceptance |
| `bluez-selection`, `portal-selection` | Lenovo unstable package selections | Stable source passes retained BlueZ/pidfd tests; real Bluetooth/portal acceptance |
| `blueman-polkit` | Build-support override on two laptops | Stock Polkit support and unchanged actions/policy; live agent checks |
| `mesa-libc-boundary` | Stable Mesa plus isolated released kernel/NVIDIA/firmware | Keep application/Mesa libc compatibility; intentional policy, not a temporary source patch |

Per-entry references, owning files, audits and removal criteria live in the
registry. Empty upstream-reference lists mean **no recorded upstream fix**, not
a claim that none exists. FileManager, Amnezia, Yazi and OpenCode tests are not yet
generic automated unpatched-source removal contracts.

The former BlueZ 5.86 backport and deliberately dropped Kitty 0.47.0 auto-theme
backport are **already removed**. History/acceptance limits remain in
`hosts/laptop/boot-errors.md`, `docs/laptop-audit/lenovo-checklist.md` and `AGENTS.md`;
do not restore them. Archived OpenCode V1/RLM is excluded. Own scripts, wrappers
and configuration features are not all backports; coverage exclusions explain
two template-only cases.

## Automatic update review

The updated `nix-flake-update-verify` runs the checkout's checker:

1. **Before builds:** validate complete patch coverage and registered Nix source
   transformations; compare watched input and package/artifact fingerprints.
2. **After successful builds:** inspect changed entries using bounded offline
   source-path evaluation and already cached upstream sources. This second pass
   can use sources populated by those builds. No extra derivations are realized.
3. Run small unpatched-source contracts for NVIDIA, Bluetooth PM, PipeWire and the
   stable BlueZ/portal replacement candidates when a compiler/source is available
   (the native pidfd test requires Linux). Other patches get structural forward/reverse
   application probes, not an invented behavioral verdict.

The checker makes no explicit GitHub/API requests and never updates inputs,
realizes package fetchers, builds packages, modifies source directories, accepts
reviews or removes fixes. Nix is invoked with `--offline`, `--no-update-lock-file`
and `--no-write-lock-file`, not as a network-isolated sandbox; this is cached-input
inspection rather than a release-polling service. Scratch
compilation/patching happens only under `/tmp/opencode`. Source lookup has a
20-second limit. Cached tar archives are streamed in a separate 20-second process
that copies only selected regular files (8 MiB/file, 20 MiB total), never whole
kernel trees or archive links. Contracts have a 45-second group limit. Missing
source/compiler, changed code and timeouts are explicit review gaps.

Output meanings:

- `unchanged`: declared inputs/artifacts match the inventory fingerprint.
  **Not** evidence of a fresh upstream or functional review.
- `applies-not-proof`: patch applies with no fuzz/offset. This does **not** prove
  the bug persists; an equivalent upstream implementation may already exist.
- `removal-candidate`: an unpatched contract passes or exact patch text is present.
  The message distinguishes these. Neither removes anything; structural inclusion
  still requires behavioral review.
- `review-required`: changed dependency/inline fix, conflict, failed contract,
  unavailable source/tool or other unresolved evidence. Extraction/compile/assertion
  failures are never converted into “still needed”.
- `inventory-error`: malformed/incomplete registry or unregistered patch/source
  transformation. Stops the updater before builds; other findings are advisory.

There is no unconditional “still needed” verdict from a text probe. Customizations
and test-only patches are never declared obsolete by reverse matching. No periodic
service/network polling is configured. Direct `nix flake update` or source-pin
edits bypass the helper: run the checker manually or use `--no-update` afterwards.
Failed builds stop before the post-build pass; run it manually when useful.
Unrelated input updates do not trigger source probes for unchanged entries.

## Manual review and maintenance

From the repository root, without activation:

```fish
# Coverage/fingerprints only; no Nix evaluation or compilation.
python3 -B scripts/backport-review.py

# One fix, cached sources and its small removal contract.
python3 -B scripts/backport-review.py --only nvidia-init-root --all --cached --contracts

# Or an explicitly supplied UNMODIFIED source directory.
python3 -B scripts/backport-review.py --only btintel-pm --source kernel=/path/to/linux --contracts

# All cached-source checks, with the limits described above.
python3 -B scripts/backport-review.py --all --cached --contracts

# Synthetic tests: no real updates/builds/network.
python3 -B scripts/test_backport_review.py
python3 -B home/core-set/test_flake_update_verify.py
```

`reviewed.json` records initial inventory fingerprints, **not** new functional
verification of every carried fix. Investigate changed entries using their
criteria, keep regression scenarios and record results in the relevant audit.
`--snapshot` prints proposed fingerprints; it never writes/accepts them. Update
only relevant keys manually after review. Do not blanket-reset outstanding
reviews. Input keys are shared: acknowledging one acknowledges every entry
watching it, so review those entries together or leave that input key unchanged.

Coverage scans all active `.patch` files and Nix files containing `overrideAttrs`,
`substituteInPlace`, `fetchpatch` or `boot.kernelPatches`. This is a safety net,
**not** a semantic detector for arbitrary future inline workarounds. Register new
ones deliberately. Local source pins are covered by owning-file hashes; declared
root inputs use locked-source fingerprints (including followed aliases), not a
live upstream release feed.

### Preparation checks

The 22 synthetic checker scenarios and four generated-updater/mock-command
scenarios pass without real updates/builds. NVIDIA's actual-function harness
reproduces the baseline failures and passes eight patched compile variants;
selected merged Nix checks confirm unchanged kernel/userspace/sleep policy and
module delivery. The runtime-PM and declaration fixtures pass too.

The common checker was exercised against cached selected NVIDIA and stable BlueZ
sources: their unpatched contracts returned `review-required`, not a removal
candidate. Stable portal source was not cached, so that check was explicitly not
run. This is not an all-source test matrix or new UI/hardware acceptance. Nixfmt
and non-patch whitespace checks pass; Prettier/Ruff were unavailable. The exact
upstream NVIDIA diff retains two single-space blank context lines: these are diff
syntax, not source trailing whitespace, and are not rewritten to silence Git's
whole-file whitespace checker. No package build,
activation or driver operation was performed by the agent. The user subsequently
built/applied the Lenovo system and confirmed idle/offload plus one Hibernate/
offload/idle cycle; static/live evidence and acceptance limits are in the graphics
audit. The user then applied HM: installed helper `qbm2l45z...` contains the new
checkout checker and post-build cached/contracts hook, and installed Bash syntax
passes. Direct checker output is `unchanged=26`, not fresh upstream verification.
A real update/build cycle through this installed hook has not been exercised by
the agent; the generated-updater/mock tests remain the end-to-end flow coverage.

## Applying these changes

- NVIDIA: NixOS `laptop` only, no Home Manager change for the module. User-run
  build/apply/reboot and RTD3 acceptance are in the
  [graphics audit](../laptop-audit/graphics.md).
  Git-backed `.#` excludes untracked files: review/stage the new patch before
   those commands. Initial preparation did not stage/commit files; the user later
   authorized final review and a local commit of the accepted work.
- Automatic helper hook: Home Manager for the relevant profile, e.g.
  `home-manager switch --flake .#samov-laptop`. Until applied, use the checkout
  script directly. `--no-update` also checks repository changes.
- Registry/scripts/audits: direct use needs no Nix activation. No timer, firmware
  operation, driver reload/rebind or extra power hook was added.
