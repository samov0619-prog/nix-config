#pragma once

namespace hypr_spaces {

struct PreviewBox {
    float x;
    float y;
    float width;
    float height;

    constexpr bool operator==(const PreviewBox&) const = default;
};

constexpr PreviewBox targetPixelsToLogical(const PreviewBox& box, float targetScale) {
    return {box.x / targetScale, box.y / targetScale, box.width / targetScale, box.height / targetScale};
}

} // namespace hypr_spaces
