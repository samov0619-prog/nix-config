#include "preview_geometry.hpp"

#include <cassert>

int main() {
    using hypr_spaces::PreviewBox;
    using hypr_spaces::targetPixelsToLogical;

    assert((targetPixelsToLogical({100.F, 50.F, 800.F, 400.F}, 1.F) == PreviewBox{100.F, 50.F, 800.F, 400.F}));
    assert((targetPixelsToLogical({100.F, 50.F, 800.F, 400.F}, 1.25F) == PreviewBox{80.F, 40.F, 640.F, 320.F}));
    assert((targetPixelsToLogical({100.F, 50.F, 800.F, 400.F}, 2.F) == PreviewBox{50.F, 25.F, 400.F, 200.F}));
}
