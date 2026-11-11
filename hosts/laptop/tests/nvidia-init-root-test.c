/* Mock kernel contracts around actual NVIDIA functions; no native kernel API. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NV_FILESYSTEM_ACCESS_AVAILABLE 1
#define NV_CHECK_EXPORT_SYMBOL(x) EXPORT_INIT_FS
#define NV_PCI_DOMAIN_NUMBER(p) ((p)->domain)
#define NV_PCI_BUS_NUMBER(p) ((p)->bus)
#define NV_PCI_SLOT_NUMBER(p) ((p)->slot)
#define O_RDONLY 0
#define IS_ERR(p) ((p) == (void *)(intptr_t)-1)
#define smp_load_acquire(p) (*(p))
#define NV_KZALLOC(p, n) ((p) = alloc_failure ? NULL : calloc(1, (n)))
#define NV_KFREE(p, n) free(p)
#define nv_printf(...) ((void)0)
#define dev_name(p) "fixture"

struct super_block { const char *s_id; };
struct inode { struct super_block *i_sb; };
struct file { struct inode *f_inode; void *private_data; };
struct seq_file { struct file *file; void *op; void *private; };
struct kernfs_open_file { struct file *file; struct seq_file *seq_file; };
struct pci_dev { unsigned domain, bus, slot; int dev; };
struct pci_device_id { int unused; };
struct task_struct { int unused; };
typedef struct { struct file *sysfs_config_file; } nv_linux_state_t;
typedef struct {
    struct pci_dev *pci_dev;
    const struct pci_device_id *id_table;
    int done, rc;
} nv_pci_probe_deferred_context_t;

static int root_is_init, open_failure, alloc_failure, thread_failure;
static int closes, workers, bodies, opened_in_init;
static bool nv_pci_driver_registration_in_progress;
static struct super_block sb;
static struct inode inode;
static struct file config;
static struct seq_file sf;
static struct kernfs_open_file of;
static nv_linux_state_t nvl;

static inline void restore_root(int *old) { root_is_init = *old; }
#define scoped_with_init_fs() \
    for (int old __attribute__((cleanup(restore_root))) = root_is_init, \
         once = (root_is_init = 1); once; once = 0)

static struct file *filp_open(const char *name, int flags, int mode)
{
    assert(strcmp(name, "/sys/bus/pci/devices/0000:02:00.0/config") == 0);
    assert(flags == O_RDONLY && mode == 0);
    opened_in_init = root_is_init;
    return !root_is_init || open_failure ? (void *)(intptr_t)-1 : &config;
}
#ifdef NV_SEQ_READ_ITER_PRESENT
static int filp_close(struct file *file, void *unused)
{
    assert(file == &config && unused == NULL);
    closes++;
    return 0;
}
#endif
static void init_completion(int *done) { *done = 0; }
static void wait_for_completion(int *done) { assert(*done); }
static int nv_pci_probe_body(struct pci_dev *, const struct pci_device_id *);
static int nv_pci_probe_deferred_worker(void *);
static struct task_struct *kthread_run(int (*worker)(void *), void *ctx,
                                      const char *format, const char *name)
{
    static struct task_struct task;
    assert(format && name);
    workers++;
    if (thread_failure) return (void *)(intptr_t)-1;
    int old = root_is_init;
    root_is_init = 0; /* Linux 7.3 kthread nullfs contract, mocked */
    worker(ctx);
    root_is_init = old;
    return &task;
}

/* ACTUAL_FUNCTIONS */

static int nv_pci_probe_body(struct pci_dev *dev, const struct pci_device_id *id)
{
    assert(id != NULL);
    bodies++;
    nv_get_pci_sysfs_config(dev, &nvl);
    return 17;
}
static int nv_pci_probe_deferred_worker(void *data)
{
    nv_pci_probe_deferred_context_t *ctx = data;
    ctx->rc = nv_pci_probe_body(ctx->pci_dev, ctx->id_table);
    ctx->done = 1;
    return 0;
}
static void reset(void)
{
    root_is_init = open_failure = alloc_failure = thread_failure = 0;
    closes = workers = bodies = opened_in_init = 0;
    nvl.sysfs_config_file = NULL;
    sb.s_id = "sysfs";
    inode.i_sb = &sb;
    config.f_inode = &inode;
    config.private_data = &sf;
    sf = (struct seq_file){ .file = &config, .private = &of };
    of = (struct kernfs_open_file){ .file = &config, .seq_file = &sf };
}
int main(void)
{
    struct pci_dev dev = { .bus = 2 };
    struct pci_device_id id = {0};
    const int scoped = EXPECT_FIXED && EXPORT_INIT_FS;
    reset();
    nv_get_pci_sysfs_config(&dev, &nvl);
    assert((nvl.sysfs_config_file != NULL) == scoped);
    assert(opened_in_init == scoped && root_is_init == 0);
    reset();
    root_is_init = 1;
    nv_get_pci_sysfs_config(&dev, &nvl);
    assert(nvl.sysfs_config_file == &config && root_is_init == 1);
    reset();
    root_is_init = open_failure = 1;
    nv_get_pci_sysfs_config(&dev, &nvl);
    assert(nvl.sysfs_config_file == NULL && closes == 0 && root_is_init == 1);
    reset();
    open_failure = 1;
    nv_get_pci_sysfs_config(&dev, &nvl);
    assert(nvl.sysfs_config_file == NULL && closes == 0 && root_is_init == 0);
    assert(opened_in_init == scoped);
#ifdef NV_SEQ_READ_ITER_PRESENT
    for (int invalid = 0; invalid < 9; invalid++) {
        reset();
        root_is_init = 1;
        switch (invalid) {
        case 0: config.f_inode = NULL; break;
        case 1: inode.i_sb = NULL; break;
        case 2: sb.s_id = "not-sysfs"; break;
        case 3: config.private_data = NULL; break;
        case 4: sf.file = NULL; break;
        case 5: sf.op = &sf; break;
        case 6: sf.private = NULL; break;
        case 7: of.file = NULL; break;
        case 8: of.seq_file = NULL; break;
        }
        nv_get_pci_sysfs_config(&dev, &nvl);
        assert(nvl.sysfs_config_file == NULL && closes == 1);
        assert(root_is_init == 1);
    }
#endif
    for (int registration = 0; registration <= 1; registration++) {
        for (int failure = 0; failure < 3; failure++) {
            reset();
            root_is_init = 1;
            nv_pci_driver_registration_in_progress = registration;
            alloc_failure = failure == 1;
            thread_failure = failure == 2;
            assert(nv_pci_probe(&dev, &id) == 17);
            int deferred = registration && !(EXPECT_FIXED && !NV_PCI_ASYNC_PROBE_SUPPORTED);
            assert(workers == (deferred && !alloc_failure));
            assert(bodies == 1 && root_is_init == 1);
            int success = !deferred || failure || scoped;
            assert((nvl.sysfs_config_file != NULL) == success);
        }
    }
    return 0;
}
