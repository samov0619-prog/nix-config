project('hypr-spaces', 'cpp',
  version: '0.0.0',
  default_options: ['buildtype=release', 'cpp_std=c++23'],
)

shared_module('hypr-spaces', 'src/main.cpp',
  dependencies: [dependency('hyprland')],
  cpp_args: ['-DWLR_USE_UNSTABLE'],
  install: true,
)

monitor_layout_test = executable('monitor-layout-test', 'tests/monitor_layout_test.cpp',
  include_directories: include_directories('src'),
)
test('monitor layout', monitor_layout_test)

workspace_allocator_test = executable('workspace-allocator-test', 'tests/workspace_allocator_test.cpp',
  include_directories: include_directories('src'),
)
test('workspace allocator', workspace_allocator_test)

canvas_model_test = executable('canvas-model-test', 'tests/canvas_model_test.cpp',
  include_directories: include_directories('src'),
)
test('canvas model and activation', canvas_model_test)

preview_geometry_test = executable('preview-geometry-test', 'tests/preview_geometry_test.cpp',
  include_directories: include_directories('src'),
)
test('preview geometry', preview_geometry_test)
