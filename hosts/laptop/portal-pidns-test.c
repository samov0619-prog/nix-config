/* Real upstream function and Linux syscalls; only GLib diagnostics are stubbed. */
#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

typedef bool gboolean;
typedef int GError;
static GError last_error;
#define TRUE true
#define FALSE false
#define G_IO_ERROR 0
#define g_io_error_from_errno(value) (value)
#define g_return_val_if_fail(condition, value) do { if (!(condition)) return (value); } while (0)
#define g_set_error(dest, domain, code, ...) do { last_error = (code); if (dest) *(dest) = &last_error; } while (0)
#define PIDFS_IOCTL_MAGIC 0xFF
#define PIDFD_GET_PID_NAMESPACE _IO(PIDFS_IOCTL_MAGIC, 5)

#if !BASELINE
static void close_fd(int *fd) { if (*fd >= 0) close(*fd); }
#define g_autofd __attribute__((cleanup(close_fd)))
#endif

/* UPSTREAM_FUNCTION */

#if !BASELINE
static int descriptor_count(void)
{
    DIR *dir = opendir("/proc/self/fd");
    assert(dir);
    int count = 0;
    while (readdir(dir)) count++;
    closedir(dir);
    return count;
}
#endif

int main(void)
{
    int fd = syscall(SYS_pidfd_open, getpid(), 0);
    int proc = open("/proc/self", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    assert(fd >= 0 && proc >= 0);
    struct stat expected;
    assert(fstatat(proc, "ns/pid", &expected, 0) == 0);
    ino_t ns = 0;
    GError *error = NULL;
#if BASELINE
    assert(!query(fd, &ns, &error));
    assert(error && *error == ENOTDIR);
    assert(query(proc, &ns, &error));
    assert(ns == expected.st_ino);
    puts("1.20.4: real pidfd reproduces ENOTDIR; proc dirfd succeeds");
#else
    int before = descriptor_count();
    for (int i = 0; i < 32; i++) {
        error = NULL;
        assert(query(fd, &ns, &error));
        assert(!error && ns == expected.st_ino);
    }
    assert(descriptor_count() == before);
    assert(!query(proc, &ns, &error));
    assert(error && *error == ENOTTY);
    int closed = dup(fd);
    assert(closed >= 0);
    close(closed);
    assert(!query(closed, &ns, &error));
    assert(error && *error == EBADF);
    assert(!query(-1, &ns, &error));
    assert(!query(fd, NULL, &error));
    puts("fixed: correct namespace, no fd leak, wrong/closed/invalid descriptor guards passed");
#endif
    close(proc);
    close(fd);
    return 0;
}
