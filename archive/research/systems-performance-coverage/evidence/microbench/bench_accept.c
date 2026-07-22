/* Darwin accept()+SO_RCVTIMEO verification.
 * Flag: the member audit specifies listener-SO_RCVTIMEO timed accept as the
 * graceful-drain mechanism and requires verifying accept HONORS the timeout on
 * macOS. setsockopt(SO_RCVTIMEO) on a *listening* socket is the folklore-
 * disputed case; that is what Test 1 settles.
 * Platform: Apple M4, macOS (indicative; deploy target Linux x86-64).
 *
 * Method: SO_RCVTIMEO = 1s; alarm(4) is a safety net installed WITHOUT
 * SA_RESTART so a truly-blocked syscall returns EINTR at 4s. Discriminator:
 *   accept/read returns EAGAIN/EWOULDBLOCK at ~1s  => timeout HONORED
 *   accept/read returns EINTR at ~4s (alarm)       => timeout IGNORED (blocks forever)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <netinet/in.h>
#include <arpa/inet.h>

static void on_alarm(int sig) { (void)sig; /* no-op; just interrupts the syscall */ }

static double now_s(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static void install_alarm(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_alarm;
    sa.sa_flags = 0; /* NO SA_RESTART => blocking syscalls return EINTR */
    sigaction(SIGALRM, &sa, NULL);
}

static int make_listener(int *out_port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket"); exit(1); }
    int one = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    struct sockaddr_in a;
    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = 0; /* ephemeral */
    if (bind(fd, (struct sockaddr *)&a, sizeof(a)) < 0) { perror("bind"); exit(1); }
    if (listen(fd, 16) < 0) { perror("listen"); exit(1); }
    socklen_t sl = sizeof(a);
    getsockname(fd, (struct sockaddr *)&a, &sl);
    *out_port = ntohs(a.sin_port);
    return fd;
}

int main(void) {
    printf("== Darwin accept + SO_RCVTIMEO ==\n");
    printf("platform: Apple M4, macOS aarch64 (indicative; deploy target Linux x86-64)\n");
    printf("errno constants here: EAGAIN=%d EWOULDBLOCK=%d EINTR=%d\n\n", EAGAIN, EWOULDBLOCK, EINTR);
    install_alarm();

    /* Test 1: SO_RCVTIMEO on the LISTENING socket; accept() with NO client. */
    {
        int port;
        int L = make_listener(&port);
        struct timeval tv = { .tv_sec = 1, .tv_usec = 0 };
        int rc = setsockopt(L, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        printf("[Test 1] listening port=%d  setsockopt(SO_RCVTIMEO=1.0s) rc=%d (%s)\n",
               port, rc, rc == 0 ? "ok" : strerror(errno));
        alarm(4);
        double t0 = now_s();
        struct sockaddr_in peer; socklen_t pl = sizeof(peer);
        int c = accept(L, (struct sockaddr *)&peer, &pl);
        int e = errno;
        double dt = now_s() - t0;
        alarm(0);
        printf("[Test 1] accept() = %d after %.3fs, errno=%d (%s)\n",
               c, dt, c < 0 ? e : 0, c < 0 ? strerror(e) : "ok");
        if (c < 0 && (e == EAGAIN || e == EWOULDBLOCK) && dt < 3.0)
            printf("[Test 1] VERDICT: accept HONORS listener SO_RCVTIMEO on this macOS "
                   "(EAGAIN at ~1s) => timed-accept drain WORKS on Darwin.\n");
        else if (c < 0 && e == EINTR)
            printf("[Test 1] VERDICT: accept IGNORES listener SO_RCVTIMEO on this macOS "
                   "(blocked until the 4s alarm) => timed-accept drain is WRONG on Darwin; "
                   "need kqueue/poll drain or loopback self-connect wakeup.\n");
        else
            printf("[Test 1] VERDICT: INCONCLUSIVE (unexpected: c=%d e=%d dt=%.3f).\n", c, e, dt);
        if (c >= 0) close(c);
        close(L);
    }
    printf("\n");

    /* Test 2: SO_RCVTIMEO on an ACCEPTED socket; client connects, sends nothing. */
    {
        int port;
        int L = make_listener(&port);
        pid_t pid = fork();
        if (pid == 0) {
            int s = socket(AF_INET, SOCK_STREAM, 0);
            struct sockaddr_in a;
            memset(&a, 0, sizeof(a));
            a.sin_family = AF_INET;
            a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
            a.sin_port = htons(port);
            if (connect(s, (struct sockaddr *)&a, sizeof(a)) < 0) { perror("child connect"); _exit(2); }
            sleep(5);      /* stay connected, send nothing */
            close(s);
            _exit(0);
        }
        struct sockaddr_in peer; socklen_t pl = sizeof(peer);
        int conn = accept(L, (struct sockaddr *)&peer, &pl);
        if (conn < 0) { perror("[Test 2] accept"); }
        struct timeval tv = { .tv_sec = 1, .tv_usec = 0 };
        int rc = setsockopt(conn, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        printf("[Test 2] accepted conn fd=%d  setsockopt(SO_RCVTIMEO=1.0s) rc=%d (%s)\n",
               conn, rc, rc == 0 ? "ok" : strerror(errno));
        alarm(4);
        char buf[64];
        double t0 = now_s();
        ssize_t n = read(conn, buf, sizeof(buf));
        int e = errno;
        double dt = now_s() - t0;
        alarm(0);
        printf("[Test 2] read() = %zd after %.3fs, errno=%d (%s)\n",
               n, dt, n < 0 ? e : 0, n < 0 ? strerror(e) : "ok");
        if (n < 0 && (e == EAGAIN || e == EWOULDBLOCK) && dt < 3.0)
            printf("[Test 2] VERDICT: read HONORS SO_RCVTIMEO on the accepted socket "
                   "(EAGAIN at ~1s) => per-stream RCVTIMEO deadline WORKS (expected/standard).\n");
        else if (n < 0 && e == EINTR)
            printf("[Test 2] VERDICT: read IGNORES SO_RCVTIMEO (blocked until alarm).\n");
        else
            printf("[Test 2] VERDICT: INCONCLUSIVE (n=%zd e=%d dt=%.3f).\n", n, e, dt);
        if (conn >= 0) close(conn);
        close(L);
        int st; waitpid(pid, &st, 0);
    }
    return 0;
}
