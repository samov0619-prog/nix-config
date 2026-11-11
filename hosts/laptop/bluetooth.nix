{ pkgsUnstable, ... }:
{
  # Pinned unstable already includes the empty-default-list fix; no local patch.
  # Only this daemon/tool package changes, not Blueman or other hosts.
  hardware.bluetooth.package = pkgsUnstable.bluez;

  # Independent of BlueZ: backport the upstream PCIe PM fixes, Lenovo only.
  # Keep tests/removal instructions in bluetooth-pm.md when updating the kernel.
  boot.kernelPatches = [
    {
      name = "btintel-pcie-refresh-dstate";
      patch = ./btintel-pcie-refresh-dstate.patch;
    }
    {
      name = "btintel-pcie-pm-flow";
      patch = ./btintel-pcie-pm-flow.patch;
    }
  ];
  warnings = [
    "BTINTEL PM CLEANUP: Lenovo carries two upstream btintel_pcie PM backports. On kernel updates, check the unpatched source with test_btintel_pm.py --check-upstream; see hosts/laptop/bluetooth-pm.md. A patch conflict alone does not prove the fixes are included."
  ];
}
