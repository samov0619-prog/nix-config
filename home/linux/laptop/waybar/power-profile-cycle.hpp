#pragma once

#include <cstddef>
#include <optional>

namespace waybar::modules {

// Shared by the tooltip and click handler; preserve PPD's actual list order.
inline std::optional<std::size_t> powerProfileCycleIndex(std::size_t count,
                                                       std::size_t active,
                                                       bool forward) {
  if (count == 0 || active >= count) return std::nullopt;
  if (forward) return active + 1 == count ? 0 : active + 1;
  return active == 0 ? count - 1 : active - 1;
}

}  // namespace waybar::modules
