#pragma once

#include <algorithm>
#include <ranges>
#include <vector>

namespace hypr_spaces {

struct MonitorRect {
    int id;
    int x;
    int y;
    int width;
    int height;
};

struct MonitorGroup {
    std::vector<int> monitorIDs;
};

// Outputs whose vertical spans overlap belong to one visual row. The transitive
// case matters for staggered layouts: A can overlap B while B overlaps C.
inline std::vector<MonitorGroup> groupMonitorsInVisualRows(std::vector<MonitorRect> monitors) {
    std::ranges::sort(monitors, {}, [](const auto& monitor) {
        return std::pair{monitor.y, monitor.x};
    });

    std::vector<MonitorGroup> rows;
    for (size_t first = 0; first < monitors.size();) {
        size_t last = first + 1;
        int rowBottom = monitors[first].y + monitors[first].height;
        for (; last < monitors.size() && monitors[last].y < rowBottom; ++last)
            rowBottom = std::max(rowBottom, monitors[last].y + monitors[last].height);

        auto& row = rows.emplace_back();
        std::ranges::sort(monitors.begin() + first, monitors.begin() + last, {}, &MonitorRect::x);
        for (size_t index = first; index < last; ++index)
            row.monitorIDs.push_back(monitors[index].id);
        first = last;
    }
    return rows;
}

inline std::vector<int> monitorTabOrder(const std::vector<MonitorRect>& monitors) {
    auto rows = groupMonitorsInVisualRows(monitors);
    std::vector<int> order;
    for (const auto& row : rows)
        order.insert(order.end(), row.monitorIDs.begin(), row.monitorIDs.end());
    return order;
}

} // namespace hypr_spaces
