#define _GNU_SOURCE
#include <errno.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <linux/capability.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static void check(int value, const char *label) { if (value < 0) { perror(label); exit(125); } }
static void limit(int resource, rlim_t value) { struct rlimit bound = {value, value}; check(setrlimit(resource, &bound), "rlimit"); }
static void directory(const char *path) { check(mkdir(path, 0755), path); }
static void bind_ro(const char *source, const char *dest) {
    check(mount(source, dest, NULL, MS_BIND, NULL), source);
    check(mount(NULL, dest, NULL, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV, NULL), dest);
}
#define DENY(number) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, number, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)
int main(int argc, char **argv) {
    if (argc != 3) return 125;
    check(mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL), "private mounts");
    check(mount("tmpfs", argv[1], "tmpfs", MS_NOSUID | MS_NODEV, "size=64m,nr_inodes=8192,mode=755"), "root tmpfs");
    check(chdir(argv[1]), "root cwd");
    directory("usr"); directory("source"); directory("scratch");
    check(symlink("usr/bin", "bin"), "bin link");
    check(symlink("usr/lib", "lib"), "lib link");
    check(symlink("usr/lib64", "lib64"), "lib64 link");
    directory("usr/bin"); directory("usr/lib"); directory("usr/lib64");
    directory("usr/lib/python3.10"); directory("usr/lib/x86_64-linux-gnu");
    directory("usr/lib/python3"); directory("usr/lib/python3/dist-packages");
    // Do not expose WSL's host integration mounts below /usr/lib/wsl.
    bind_ro("/usr/bin", "usr/bin");
    bind_ro("/usr/lib/python3.10", "usr/lib/python3.10");
    bind_ro("/usr/lib/python3/dist-packages", "usr/lib/python3/dist-packages");
    bind_ro("/usr/lib/x86_64-linux-gnu", "usr/lib/x86_64-linux-gnu");
    bind_ro("/usr/lib64", "usr/lib64");
    bind_ro(argv[2], "source");
    check(mount("tmpfs", "scratch", "tmpfs", MS_NOSUID | MS_NODEV | MS_NOEXEC,
                "size=32m,nr_inodes=4096,mode=700"), "scratch tmpfs");
    check(mount(NULL, ".", NULL, MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV, NULL), "root readonly");
    check(chroot("."), "chroot"); check(chdir("/scratch"), "scratch cwd");
    clearenv();
    setenv("PATH", "/usr/bin:/bin", 1); setenv("HOME", "/scratch", 1);
    setenv("TMPDIR", "/scratch", 1); setenv("XDG_CACHE_HOME", "/scratch", 1);
    setenv("LANG", "C.UTF-8", 1); setenv("DASH_OFFLINE_SANDBOX", "1", 1);
    limit(RLIMIT_CPU, 20); limit(RLIMIT_AS, 512 * 1024 * 1024);
    limit(RLIMIT_FSIZE, 8 * 1024 * 1024); limit(RLIMIT_NOFILE, 64);
    limit(RLIMIT_CORE, 0); limit(RLIMIT_STACK, 8 * 1024 * 1024);
    limit(RLIMIT_NPROC, 1);
    struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct caps[2] = {{0}, {0}};
    check(syscall(SYS_capset, &header, caps), "drop capabilities");
    check(prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0), "no new privileges");
    struct sock_filter rules[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        BPF_JUMP(BPF_JMP | BPF_JGE | BPF_K, 0x40000000, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        DENY(SYS_socket), DENY(SYS_socketpair), DENY(SYS_fork), DENY(SYS_vfork),
        DENY(SYS_clone), DENY(SYS_clone3), DENY(SYS_mount), DENY(SYS_umount2),
        DENY(SYS_pivot_root), DENY(SYS_chroot), DENY(SYS_setns), DENY(SYS_unshare),
        DENY(SYS_ptrace), DENY(SYS_bpf), DENY(SYS_keyctl), DENY(SYS_perf_event_open),
        DENY(SYS_open_by_handle_at), DENY(SYS_process_vm_readv), DENY(SYS_process_vm_writev),
        DENY(SYS_io_uring_setup),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
    };
    struct sock_fprog program = {(unsigned short)(sizeof(rules) / sizeof(rules[0])), rules};
    check(prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program), "seccomp");
    for (int fd = 3; fd < 1024; fd++) close(fd);
    execl("/usr/bin/python3", "python3", "-I", "-B", "/source/tests/isolated_security_runner.py", NULL);
    perror("exec python"); return 125;
}
