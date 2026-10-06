#include "preview_geometry.hpp"

#include <cassert>

int main() {
    using hypr_spaces::PreviewBox;
    using hypr_spaces::targetPixelsToLogical;
    using hypr_spaces::windowPreviewBox;

    assert((targetPixelsToLogical({100.F, 50.F, 800.F, 400.F}, 1.F) == PreviewBox{100.F, 50.F, 800.F, 400.F}));
    assert((targetPixelsToLogical({100.F, 50.F, 800.F, 400.F}, 1.25F) == PreviewBox{80.F, 40.F, 640.F, 320.F}));
    assert((targetPixelsToLogical({100.F, 50.F, 800.F, 400.F}, 2.F) == PreviewBox{50.F, 25.F, 400.F, 200.F}));

    // The same local tiled layout must have the same preview after a move in
    // either direction, even to an output above/left of the desktop origin.
    const auto before = windowPreviewBox({20, 25, 960, 1055}, 0, 0, .5F, 100, 50);
    assert(before == windowPreviewBox({1940, 25, 960, 1055}, 1920, 0, .5F, 100, 50));
    assert(before == windowPreviewBox({-1900, -1055, 960, 1055}, -1920, -1080, .5F, 100, 50));
    // Legitimately off-monitor floating geometry must not be 'corrected'.
    assert((windowPreviewBox({1800, 100, 600, 400}, 1920, 0, .5F, 100, 50) == PreviewBox{40, 100, 300, 200}));
    // Logical->physical source scaling and preview scaling compose once.
    assert((windowPreviewBox({1960, 40, 800, 600}, 1920, 0, 2.F * .25F, 100, 50) == PreviewBox{120, 70, 400, 300}));
}
