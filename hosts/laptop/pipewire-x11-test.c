/* Actual upstream callback; X11/PipeWire dependencies are contract stubs.
 * An invalid destruction is recorded, not executed: this is not a native crash
 * reproducer, X server, audio device or full module integration test.
 */
#include <assert.h>
#include <stdio.h>

typedef struct { int unused; } Display;
struct source { int destroys; };
struct loop { int invalid_destroys; };
struct module { int scheduled; };
struct impl {
    Display *display;
    struct loop *loop;
    struct source *source;
    struct module *module;
};

#define spa_assert(condition) assert(condition)
#define pw_log_warn(...) ((void) 0)

static void pw_loop_destroy_source(struct loop *loop, struct source *source)
{
    if (!source) {
        loop->invalid_destroys++;
        return;
    }
    assert(source->destroys == 0);
    source->destroys++;
}

static void pw_impl_module_schedule_destroy(struct module *module)
{
    module->scheduled++;
}

/* UPSTREAM_CALLBACK */

int main(void)
{
    Display display = {0};
    struct loop loop = {0};
    struct source source = {0};
    struct module module = {0};
    struct impl impl = {&display, &loop, &source, &module};

    /* One disconnect consumes its source and schedules teardown. */
    x11_io_error_exit_handler(&display, &impl);
    assert(source.destroys == 1 && impl.source == NULL);
    assert(loop.invalid_destroys == 0 && module.scheduled == 1);

    /* Re-entry before deferred teardown must not destroy a NULL source. */
    x11_io_error_exit_handler(&display, &impl);
    assert(source.destroys == 1 && impl.source == NULL);
    assert(loop.invalid_destroys == EXPECT_INVALID);
    assert(module.scheduled == 2);

    /* An already detached display must also be safe. */
    struct loop detached_loop = {0};
    struct module detached_module = {0};
    struct impl detached = {&display, &detached_loop, NULL, &detached_module};
    x11_io_error_exit_handler(&display, &detached);
    assert(detached_loop.invalid_destroys == EXPECT_INVALID);
    assert(detached_module.scheduled == 1 && detached.source == NULL);

    /* Another module still owns its own source after the first disconnect. */
    struct source other_source = {0};
    struct module other_module = {0};
    struct impl other = {&display, &loop, &other_source, &other_module};
    x11_io_error_exit_handler(&display, &other);
    assert(other_source.destroys == 1 && other.source == NULL);
    assert(other_module.scheduled == 1 && source.destroys == 1);
    puts(EXPECT_INVALID ? "baseline: invalid NULL-source destruction detected"
                        : "fixed: single/repeated/detached/independent callbacks pass");
    return 0;
}
