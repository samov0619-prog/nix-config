/* Actual driver functions and PM callback table, with contract stubs only.
 * No real PCI, interrupts, firmware, workqueue or Hibernate integration.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

typedef uint32_t u32;
typedef long ktime_t;
typedef struct { int event; } pm_message_t;
enum { PM_EVENT_SUSPEND, PM_EVENT_FREEZE, PM_EVENT_HIBERNATE,
       PM_EVENT_RESUME, PM_EVENT_THAW, PM_EVENT_RESTORE };
#define PMSG_SUSPEND ((pm_message_t){ PM_EVENT_SUSPEND })
#define PMSG_FREEZE ((pm_message_t){ PM_EVENT_FREEZE })
#define PMSG_HIBERNATE ((pm_message_t){ PM_EVENT_HIBERNATE })
#define PMSG_RESUME ((pm_message_t){ PM_EVENT_RESUME })
#define PMSG_THAW ((pm_message_t){ PM_EVENT_THAW })
#define PMSG_RESTORE ((pm_message_t){ PM_EVENT_RESTORE })
enum { PM_SUSPEND_TO_IDLE, PM_SUSPEND_MEM };
static int pm_suspend_target_state;
#define BIT(n) (1U << (n))
/* UPSTREAM_STATE_DEFINITIONS */
#define BTINTEL_PCIE_CSR_BOOT_STAGE_REG 1
#define BTINTEL_PCIE_CSR_MSIX_HW_INT_CAUSES 2
#define BTINTEL_PCIE_MSIX_HW_INT_CAUSES_GP0 BIT(0)
#define BTINTEL_PCIE_DX_TRANSITION_MAX_RETRIES 3
#define BTINTEL_PCIE_CORE_HALTED 0
#define BTINTEL_PCIE_IOSF_PRR_FLR 0
#define BTINTEL_PCIE_TRIGGER_REASON_FW_ASSERT 1

struct btintel_pcie_data;
struct pci_dev { struct btintel_pcie_data *data; };
struct device { struct pci_dev *pci; };
struct btintel_pcie_data {
    struct pci_dev *pdev;
    void *hdev;
    unsigned long flags;
    int pm_sx_event, gp0_wait_q;
    bool gp0_received;
    u32 boot_stage_cache;
};
struct dev_pm_ops {
    int (*suspend)(struct device *), (*resume)(struct device *);
    int (*freeze)(struct device *), (*thaw)(struct device *);
    int (*poweroff)(struct device *), (*restore)(struct device *);
};
static struct pci_dev pci;
static struct device dev = { &pci };
static struct btintel_pcie_data data;
static u32 hardware_state;
static int reads, writes, clears, resets, dumps, errors, transitions, dx_result;
static u32 requested_state;
static bool deliver_irq, controller_error, controller_halted;
static struct pci_dev *to_pci_dev(struct device *d) { return d->pci; }
static struct btintel_pcie_data *pci_get_drvdata(struct pci_dev *p) { return p->data; }
static ktime_t ktime_get(void) { return 0; }
static long long ktime_to_us(ktime_t t) { return t; }
static void log_stub(void *hdev, const char *fmt, ...) { (void)hdev; (void)fmt; }
#define bt_dev_dbg(...) log_stub(__VA_ARGS__)
#define bt_dev_warn(...) log_stub(__VA_ARGS__)
#define bt_dev_err(...) (errors++, log_stub(__VA_ARGS__))
#define msecs_to_jiffies(ms) (ms)
#define wait_event_timeout(queue, condition, timeout) \
    ((void)(queue), (void)(timeout), (condition) ? 1L : 0L)
static void btintel_pcie_wr_sleep_cntrl(struct btintel_pcie_data *d, u32 state)
{
    writes++;
    requested_state = state;
    d->gp0_received = deliver_irq;
}
static void btintel_pcie_clr_reg_bits(struct btintel_pcie_data *d, u32 reg, u32 bits)
{
    (void)d; (void)reg; (void)bits; clears++;
}
static u32 btintel_pcie_rd_reg32(struct btintel_pcie_data *d, u32 reg)
{
    (void)d; assert(reg == BTINTEL_PCIE_CSR_BOOT_STAGE_REG); reads++;
    return hardware_state;
}
static bool btintel_pcie_in_error(struct btintel_pcie_data *d)
{
    (void)d; return controller_error;
}
static bool btintel_pcie_in_device_halt(struct btintel_pcie_data *d)
{
    (void)d; return controller_halted;
}
static void set_bit(int bit, unsigned long *flags) { *flags |= 1UL << bit; }
static void btintel_pcie_request_reset(struct btintel_pcie_data *d, int type)
{
    (void)d; assert(type == BTINTEL_PCIE_IOSF_PRR_FLR); resets++;
}
static void btintel_pcie_queue_coredump(struct btintel_pcie_data *d, int reason)
{
    (void)d; assert(reason == BTINTEL_PCIE_TRIGGER_REASON_FW_ASSERT); dumps++;
}

/* UPSTREAM_DSTATE_FUNCTIONS */

static int fake_dxstate(struct btintel_pcie_data *d, u32 state)
{
    (void)d; requested_state = state; transitions++; return dx_result;
}
#define btintel_pcie_set_dxstate fake_dxstate
/* UPSTREAM_PM_CALLBACKS */
#undef btintel_pcie_set_dxstate

static void fresh(void)
{
    data = (struct btintel_pcie_data){ .pdev = &pci };
    pci.data = &data;
    reads = writes = clears = resets = dumps = errors = transitions = dx_result = 0;
    hardware_state = requested_state = 0;
    deliver_irq = controller_error = controller_halted = false;
    pm_suspend_target_state = PM_SUSPEND_TO_IDLE;
}

int main(void)
{
    fresh();
    assert(btintel_pcie_pm_ops.freeze(&dev) == 0);
    assert(requested_state == BTINTEL_PCIE_STATE_D3_COLD);
    transitions = 0;
    assert(btintel_pcie_pm_ops.thaw(&dev) == 0);
    assert(resets == (EXPECT_FIXED ? 0 : 1));
    assert(transitions == (EXPECT_FIXED ? 1 : 0));
    if (EXPECT_FIXED) assert(requested_state == BTINTEL_PCIE_STATE_D0);

    fresh();
    assert(btintel_pcie_pm_ops.freeze(&dev) == 0);
    transitions = 0;
    assert(btintel_pcie_pm_ops.restore(&dev) == 0);
    assert(resets == 1 && transitions == 0 && data.flags != 0);

    fresh();
    assert(btintel_pcie_pm_ops.poweroff(&dev) == 0);
    assert(requested_state == BTINTEL_PCIE_STATE_D3_COLD);
    assert(btintel_pcie_pm_ops.restore(&dev) == 0 && resets == 1);

    fresh();
    assert(btintel_pcie_pm_ops.suspend(&dev) == 0);
    assert(requested_state == BTINTEL_PCIE_STATE_D3_HOT);
    assert(btintel_pcie_pm_ops.resume(&dev) == 0);
    assert(requested_state == BTINTEL_PCIE_STATE_D0 && resets == 0);

    fresh();
    pm_suspend_target_state = PM_SUSPEND_MEM;
    assert(btintel_pcie_pm_ops.suspend(&dev) == 0);
    assert(requested_state == (EXPECT_FIXED ? BTINTEL_PCIE_STATE_D3_COLD :
                                            BTINTEL_PCIE_STATE_D3_HOT));
    transitions = 0;
    assert(btintel_pcie_pm_ops.resume(&dev) == 0);
    assert(resets == (EXPECT_FIXED ? 1 : 0));
    assert(transitions == (EXPECT_FIXED ? 0 : 1));

    fresh();
    dx_result = -EBUSY;
    assert(btintel_pcie_pm_ops.suspend(&dev) == -EBUSY);
    assert(resets == 0);
    assert(btintel_pcie_pm_ops.resume(&dev) == -EBUSY);
    assert(resets == 0 && dumps == 0);

    for (int halted = 0; halted < 2; halted++) {
        fresh();
        assert(btintel_pcie_pm_ops.suspend(&dev) == 0);
        dx_result = -EBUSY;
        controller_halted = halted;
        controller_error = !halted;
        assert(btintel_pcie_pm_ops.resume(&dev) == -EBUSY);
        assert(resets == 1 && dumps == 1 && data.flags != 0);
    }

    /* Missed IRQ, but hardware reached the requested state: stale cache must
     * not force EBUSY. Exercise the actual set_dxstate(), not fake_dxstate(). */
    for (int d3 = 0; d3 < 2; d3++) {
        fresh();
        hardware_state = d3 ? BTINTEL_PCIE_CSR_BOOT_STAGE_D3_STATE_READY : 0;
        data.boot_stage_cache = d3 ? 0 : BTINTEL_PCIE_CSR_BOOT_STAGE_D3_STATE_READY;
        u32 target = d3 ? BTINTEL_PCIE_STATE_D3_COLD : BTINTEL_PCIE_STATE_D0;
        assert(btintel_pcie_set_dxstate(&data, target) == (EXPECT_FIXED ? 0 : -EBUSY));
        assert(writes == (EXPECT_FIXED ? 1 : 3));
        assert(reads == (EXPECT_FIXED ? 1 : 0));
    }

    fresh();
    hardware_state = data.boot_stage_cache = BTINTEL_PCIE_CSR_BOOT_STAGE_D3_STATE_READY;
    assert(btintel_pcie_set_dxstate(&data, BTINTEL_PCIE_STATE_D0) == -EBUSY);
    assert(writes == 3 && clears == 3);

    fresh();
    deliver_irq = true;
    assert(btintel_pcie_set_dxstate(&data, BTINTEL_PCIE_STATE_D0) == 0);
    assert(writes == 1 && reads == 0 && clears == 0);
    puts(EXPECT_FIXED ? "PASS: 12 fixed PM/D-state contract cases" :
                        "PASS: baseline thaw/S3/stale-cache defects reproduced; other contracts retained");
    return 0;
}
