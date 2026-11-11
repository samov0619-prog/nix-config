// Tiny local unit test, not a Waybar build or GTK/DBus integration test.
#include "../power-profile-cycle.hpp"

#include <cassert>
#include <string>
#include <vector>

int main() {
  using waybar::modules::powerProfileCycleIndex;
  assert(!powerProfileCycleIndex(0, 0, true));
  assert(!powerProfileCycleIndex(0, 0, false));
  assert(!powerProfileCycleIndex(3, 3, true));
  assert(!powerProfileCycleIndex(3, 99, false));
  assert(powerProfileCycleIndex(1, 0, true) == 0);
  assert(powerProfileCycleIndex(1, 0, false) == 0);
  for (bool forward : {false, true}) {
    assert(powerProfileCycleIndex(2, 0, forward) == 1);
    assert(powerProfileCycleIndex(2, 1, forward) == 0);
  }
  const std::vector<std::string> profiles = {"power-saver", "balanced", "performance"};
  for (std::size_t i = 0; i < profiles.size(); ++i) {
    assert(powerProfileCycleIndex(3, i, true) == (i + 1) % 3);
    assert(powerProfileCycleIndex(3, i, false) == (i + 2) % 3);
  }
  assert(profiles[*powerProfileCycleIndex(3, 1, false)] == "power-saver");
  assert(profiles[*powerProfileCycleIndex(3, 1, true)] == "performance");
  // Neither a third profile nor canonical sorting is assumed.
  const std::vector<std::string> custom = {"vendor-mode", "balanced"};
  assert(custom[*powerProfileCycleIndex(custom.size(), 1, true)] == "vendor-mode");
  assert(custom[*powerProfileCycleIndex(custom.size(), 0, false)] == "balanced");
}
