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

// Window geometry is global logical; monitor origins may be negative and
// floating windows may cross their owner's boundary. Never clamp/guess origin.
constexpr PreviewBox windowPreviewBox(const PreviewBox& global, float sourceX, float sourceY,
                                      float logicalToPreviewScale, float previewX, float previewY) {
    return {previewX + (global.x - sourceX) * logicalToPreviewScale,
            previewY + (global.y - sourceY) * logicalToPreviewScale,
            global.width * logicalToPreviewScale, global.height * logicalToPreviewScale};
}

} // namespace hypr_spaces
