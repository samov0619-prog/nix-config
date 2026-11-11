/* Stubs around the actual upstream load_defaults(), not a replacement for it. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>

#define KERNEL_SET_SYSTEM_CONFIG 1
#define MGMT_OP_SET_DEF_SYSTEM_CONFIG 2

struct btd_adapter { void *mgmt; unsigned int dev_id; };
struct mgmt_tlv_list { unsigned int size; };
static struct { struct { int num_entries, br, le; } defaults; } btd_opts;
static struct mgmt_tlv_list list;
static int errors, frees, sends;
static bool supported, br_ok, le_ok;
static unsigned int send_result;

static bool btd_has_kernel_features(int feature)
{
    assert(feature == KERNEL_SET_SYSTEM_CONFIG);
    return supported;
}

static struct mgmt_tlv_list *mgmt_tlv_list_new(void) { return &list; }
static unsigned int mgmt_tlv_list_size(struct mgmt_tlv_list *p) { return p->size; }
static void mgmt_tlv_list_free(struct mgmt_tlv_list *p) { assert(p == &list); frees++; }
#define load_bredr_defaults(adapter, list, options) \
    ((void)(adapter), (void)(list), (void)(options), br_ok)
#define load_le_defaults(adapter, list, options) \
    ((void)(adapter), (void)(list), (void)(options), le_ok)
#define mgmt_send_tlv(...) (sends++, send_result)
#define btd_error(...) (errors++)

/* LOAD_DEFAULTS_FUNCTION */

static void scenario(int entries, bool kernel, bool br, bool le,
                     unsigned int size, unsigned int result,
                     int expected_errors, int expected_sends, int expected_frees)
{
    struct btd_adapter adapter = { NULL, 0 };
    btd_opts.defaults.num_entries = entries;
    supported = kernel;
    br_ok = br;
    le_ok = le;
    list.size = size;
    send_result = result;
    errors = frees = sends = 0;
    load_defaults(&adapter);
    assert(errors == expected_errors);
    assert(sends == expected_sends);
    assert(frees == expected_frees);
}

int main(void)
{
    scenario(0, true, true, true, 0, 1, 0, 0, 0);
    scenario(1, false, true, true, 0, 1, 0, 0, 0);
    scenario(1, true, true, true, 0, 1, EXPECT_EMPTY_ERROR, 0, 1);
    scenario(1, true, true, true, 2, 1, 0, 1, 1);
    scenario(1, true, true, true, 2, 0, 1, 1, 1);
    scenario(1, true, false, true, 2, 1, 1, 0, 1);
    scenario(1, true, true, false, 2, 1, 1, 0, 1);
    return 0;
}
