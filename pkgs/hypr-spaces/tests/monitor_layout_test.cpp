#include "monitor_layout.hpp"

#include <cassert>
#include <vector>

int main() {
    using hypr_spaces::MonitorRect;
    using hypr_spaces::monitorTabOrder;

    assert((monitorTabOrder({
        {1, 100, 0, 100, 100},
        {2, 0, 120, 100, 100},
        {3, 100, 125, 100, 100},
        {4, 200, 120, 100, 100},
        {5, 100, 240, 100, 100},
    }) == std::vector{1, 2, 3, 4, 5}));

    assert((monitorTabOrder({
        {3, 200, 80, 100, 100},
        {1, 0, 0, 100, 100},
        {2, 100, 40, 100, 100},
    }) == std::vector{1, 2, 3}));

    assert((monitorTabOrder({
        {2, 0, 100, 100, 100},
        {1, 100, 0, 100, 100},
    }) == std::vector{1, 2}));
}
