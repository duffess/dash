#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/capability.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <sched.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static void check(int result,const char *label){if(result<0){perror(label);exit(125);}}
static void bound(int resource,rlim_t value){struct rlimit limit={value,value};check(setrlimit(resource,&limit),"rlimit");}
static void directory(const char *path){check(mkdir(path,0755),path);}
static void readonly(const char *source,const char *target){check(mount(source,target,NULL,MS_BIND,NULL),source);check(mount(NULL,target,NULL,MS_BIND|MS_REMOUNT|MS_RDONLY|MS_NOSUID|MS_NODEV,NULL),target);}
#define DENY(number) BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,number,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM)
int main(int argc,char **argv){
    // rootfs, source, standalone-Python prefix, deps, Node prefix, node_modules, mode
    if(argc!=8 || getuid()==0)return 125;
    int probe=strcmp(argv[7],"probe")==0;
    int frontend=strcmp(argv[7],"frontend")==0 || probe;
    if(!frontend && strcmp(argv[7],"python")!=0)return 125;
    check(mount(NULL,"/",NULL,MS_REC|MS_PRIVATE,NULL),"private mounts");
    check(mount("tmpfs",argv[1],"tmpfs",MS_NOSUID|MS_NODEV,"size=32m,nr_inodes=4096,mode=755"),"root tmpfs");
    check(chdir(argv[1]),"root cwd");
    directory("usr");directory("usr/bin");directory("usr/lib");directory("usr/lib64");
    directory("usr/lib/x86_64-linux-gnu");directory("source");directory("scratch");
    directory("python");directory("deps");directory("node");directory("dev");
    check(symlink("usr/bin","bin"),"bin symlink");check(symlink("usr/lib","lib"),"lib symlink");check(symlink("usr/lib64","lib64"),"lib64 symlink");
    readonly("/usr/bin","usr/bin");readonly("/usr/lib/x86_64-linux-gnu","usr/lib/x86_64-linux-gnu");readonly("/usr/lib64","usr/lib64");
    readonly(argv[2],"source");readonly(argv[3],"python");readonly(argv[4],"deps");readonly(argv[5],"node");
    readonly(argv[6],"source/my-app/node_modules");
    int nullfd=open("dev/null",O_WRONLY|O_CREAT|O_EXCL,0666);check(nullfd,"null placeholder");close(nullfd);
    // A single null sink, not a host filesystem or device tree.
    check(mount("/dev/null","dev/null",NULL,MS_BIND,NULL),"null sink");
    int randomfd=open("dev/urandom",O_WRONLY|O_CREAT|O_EXCL,0444);check(randomfd,"entropy placeholder");close(randomfd);
    check(mount("/dev/urandom","dev/urandom",NULL,MS_BIND,NULL),"entropy source");
    check(mount(NULL,"dev/urandom",NULL,MS_BIND|MS_REMOUNT|MS_RDONLY|MS_NOSUID,NULL),"entropy readonly");
    check(mount("tmpfs","scratch","tmpfs",MS_NOSUID|MS_NODEV,"size=128m,nr_inodes=8192,mode=700"),"scratch");
    check(mount(NULL,".",NULL,MS_REMOUNT|MS_RDONLY|MS_NOSUID|MS_NODEV,NULL),"root readonly");
    check(chroot("."),"chroot");check(chdir(frontend?"/source/my-app":"/scratch"),"cwd");
    // Real UID stays non-root so RLIMIT_NPROC is enforced, including children.
    cpu_set_t original,selected;CPU_ZERO(&original);CPU_ZERO(&selected);check(sched_getaffinity(0,sizeof(original),&original),"get affinity");
    int count=0;for(int cpu=0;cpu<CPU_SETSIZE && count<2;cpu++){if(CPU_ISSET(cpu,&original)){CPU_SET(cpu,&selected);count++;}}
    check(sched_setaffinity(0,sizeof(selected),&selected),"set affinity");
    clearenv();setenv("PATH","/node/bin:/usr/bin:/bin",1);setenv("HOME","/scratch",1);setenv("TMPDIR","/scratch",1);
    setenv("XDG_CACHE_HOME","/scratch",1);setenv("LANG","C.UTF-8",1);setenv("DASH_FULL_OFFLINE_SANDBOX","1",1);
    setenv("UV_THREADPOOL_SIZE","2",1);setenv("GOMAXPROCS","2",1);setenv("OMP_NUM_THREADS","2",1);setenv("OPENBLAS_NUM_THREADS","2",1);
    setenv("VITE_API_BASE_URL","https://api.example.test",1);
    bound(RLIMIT_CPU,60);bound(RLIMIT_AS,frontend?8ULL*1024*1024*1024:1024ULL*1024*1024);
    bound(RLIMIT_DATA,1024ULL*1024*1024);bound(RLIMIT_FSIZE,16*1024*1024);bound(RLIMIT_NOFILE,512);
    bound(RLIMIT_NPROC,64);bound(RLIMIT_CORE,0);bound(RLIMIT_STACK,8*1024*1024);
    struct __user_cap_header_struct header={_LINUX_CAPABILITY_VERSION_3,0};struct __user_cap_data_struct caps[2]={{0},{0}};
    check(syscall(SYS_capset,&header,caps),"drop capabilities");check(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0),"no new privileges");
    struct sock_filter rules[]={
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,arch)),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AUDIT_ARCH_X86_64,1,0),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
        BPF_JUMP(BPF_JMP|BPF_JGE|BPF_K,0x40000000,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        // Only AF_UNIX is available for asyncio/TestClient and esbuild IPC.
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_socket,1,0),BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_socketpair,0,3),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,args[0])),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AF_UNIX,1,0),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
        DENY(SYS_mount),DENY(SYS_umount2),DENY(SYS_pivot_root),DENY(SYS_chroot),DENY(SYS_setns),DENY(SYS_unshare),
        DENY(SYS_ptrace),DENY(SYS_bpf),DENY(SYS_keyctl),DENY(SYS_perf_event_open),DENY(SYS_open_by_handle_at),
        DENY(SYS_process_vm_readv),DENY(SYS_process_vm_writev),DENY(SYS_io_uring_setup),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)
    };
    struct sock_fprog program={(unsigned short)(sizeof(rules)/sizeof(rules[0])),rules};check(prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&program),"seccomp");
    for(int fd=3;fd<1024;fd++)close(fd);
    if(probe)execl("/node/bin/node","/node/bin/node","--max-old-space-size=384","--v8-pool-size=2","/source/scripts/security/frontend-probe.mjs",NULL);
    else if(frontend)execl("/node/bin/node","/node/bin/node","--max-old-space-size=384","--v8-pool-size=2","/source/scripts/security/frontend-build.mjs",NULL);
    else execl("/python/bin/python3.11","/python/bin/python3.11","-I","-B","/source/tests/isolated_full_runner.py",NULL);
    perror("exec");return 125;
}
