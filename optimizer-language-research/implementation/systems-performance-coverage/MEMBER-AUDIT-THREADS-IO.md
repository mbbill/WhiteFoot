# Member-Level Audit: threads+par, net, filemap, os

Date: 2026-07-16

Status: research result under D15/D16; closes the two blocking open flags from
`CATALOG-V1-RECUT.md` (the scheduler and residual-io pockets had no member
audit). Method: three per-pocket audits, one hostile attack that walked five
canonical programs (static-file web server, build tool, LZ4 CLI, KV store
with WAL, parallel grep) through the kept rows, one synthesis. Raw output:
`evidence/member-audit-threads-io.json`.

## Headline

- 62 members adjudicated: 33 KEEP, 9 MERGE, 10 CUT, 10 DEFER.
- The attack's FATAL: filesystem metadata/namespace (fstat, stat, readdir,
  mkdir, remove, ftruncate) was never enumerated in any pocket; six new rows
  added (~+300 trusted LOC net vs the re-cut estimate).
- All five canonical programs compose from the kept rows at par after the
  amendments.

## Row counts per pocket

```json
{
 "threads-par": {
  "KEEP": 7,
  "MERGE": 2,
  "CUT": 5,
  "DEFER": 3,
  "total": 17
 },
 "net": {
  "KEEP": 9,
  "MERGE": 4,
  "CUT": 1,
  "DEFER": 3,
  "total": 17
 },
 "filemap": {
  "KEEP": 1,
  "MERGE": 1,
  "CUT": 1,
  "DEFER": 2,
  "total": 5
 },
 "os": {
  "KEEP": 16,
  "MERGE": 2,
  "CUT": 3,
  "DEFER": 2,
  "total": 23
 },
 "all": {
  "KEEP": 33,
  "MERGE": 9,
  "CUT": 10,
  "DEFER": 10,
  "total": 62
 }
}
```

Trusted LOC delta vs re-cut: Approximately +300 trusted LOC versus the re-cut estimate (range +250 to +420). Additions: eight previously unpriced syscall-rooted capabilities dominate — fs.fstat ~40, fs.stat_path ~50, fs.readdir ~120, fs.mkdir ~20, fs.remove ~35, io.ftruncate ~25, os.proc_kill ~30, proc_try_wait extension ~20 (~+340). Removals: net_send merged into the io write row (~-60, MSG_NOSIGNAL branch deleted), net_sendv simplified to plain writev (~-15), duplicate threads-par sleep row deleted (~-15) (~-90). Contract amendments add ~+50: proc_spawn POSIX_SPAWN_SETSIGDEF/SETSIGMASK ~10, listener-typed SO_RCVTIMEO timed accept ~15, for_chunks indexed/zipped out-slot checker surface ~25. The delta is dominated by the fs-namespace seam the FATAL showed was never priced; every added row is a distinct syscall unreachable from primitives with a named 51-map consumer, so each passes D16's first prong by construction.

## Final members

- **[threads-par] scoped spawn/join (region-typed)** — KEEP
  - Consumer: server request handling (thread-per-connection workers over conc_queue); compilers' parallel pipeline stages
  - Contract: scope(|s| s.spawn(closure borrowing region-scoped &/&uniq data)); spawn fails err(EAGAIN) before the child ever runs; AMENDED (resolves stack-knob minor): spawn takes optional stack_bytes, and the spec'd explicit default (8 MiB, stated in the spec, never platform-inherited) is applied on every spawn path; child trap = process abort; scope exit blocks until every child is joined, so no borrow outlives its region.
  - Platform: Explicit default stack applied on both OSes so macOS's ~512KiB pthread default can never leak in as a dev-machine deep-recursion trap; clone vs pthread_create stays behind the seal.
- **[threads-par] unscoped/detached spawn** — CUT
  - Consumer: NONE
  - Contract: Would be a 'static-env, never-joined, leaked-at-exit thread — exactly the teardown ambiguity scoped spawn forbids. Reinstate only if a v1 scenario exhibits a thread lifetime provably un-nestable in any enclosing scope; program-lifetime scope + conc_queue covers all 51 scenarios at par.
  - Platform: Cut avoids exit-time race divergence (macOS dyld vs glibc atexit/TLS teardown ordering).
- **[threads-par] worker-pool knob: thread count + stack size** — KEEP
  - Consumer: server request handling (pool sizing); codec parallel validation (size = physical cores)
  - Contract: pool(n, stack_bytes) -> pool | err; n=0 means available_parallelism (trusted sysconf/sysctl read, unreachable from primitives); teardown: pool drop drains queue then joins all workers.
  - Platform: available_parallelism source differs (sysctl hw.* vs sched_getaffinity); Apple Silicon P/E asymmetry makes 'core count' ambiguous — spec which count each platform returns.
- **[threads-par] worker-pool knobs: pinning/affinity/priorities** — DEFER
  - Consumer: NONE in v1 (engines plausible future consumer)
  - Contract: Would be: pin worker i to cpu set / sched class at pool construction; err on EPERM/unsupported; no runtime re-pinning.
  - Platform: HIGH divergence: macOS thread_affinity_policy is a hint ignored on Apple Silicon (untestable on dev machine); SCHED_FIFO needs CAP_SYS_NICE on Linux.
- **[threads-par] par.for_chunks** — KEEP
  - Consumer: codecs: parallel validation, partition pass of parallel sort; also carrier for the par.reduce library form
  - Contract: AMENDED (resolves reduce-dependency minor): body receives (chunk_index: usize, in_chunk: &uniq [T], and optionally a zipped out-slot &uniq U drawn from a checker-split disjoint output array with the same partition); checker-proved disjointness carried across the thread boundary is the nonforgeable fact users cannot build; returns only after all chunks complete; any trap aborts the process; no early-exit channel in v1.
  - Platform: None material; chunk-size heuristics are tuning, not semantics. The new indexed/zipped out-slot shape is added checker surface and needs its own hostile fact-channel review (see open flags).
- **[threads-par] par fork-join (recursive task spawn)** — KEEP
  - Consumer: build-system-style fork-join (compilers); recursive parallel sort (codecs)
  - Contract: Inside a par scope: h = s.fork(task); v = h.join() returns the task's value; work-stealing internal; trap in any task aborts the process; par scope exit implies every forked task completed.
  - Platform: Correctness rests on internal deque memory orderings — arm64 (dev machine) is the honest stress bed; x86-64 TSO can mask fence bugs, so deploy-target green is insufficient evidence.
- **[threads-par] par.reduce (wrapping-int monoids only)** — MERGE
  - Consumer: codec checksums (adler/CRC-style) — served by the merged form
  - Contract: Checked-library helper over the AMENDED for_chunks: chunk i writes its partial into out-slot i of a preallocated disjoint output array (now expressible — for_chunks passes chunk_index and a zipped &uniq out-slot), then a serial O(chunks) fold; wrapping-int monoids make combine order-insensitive, so at par with a fused builtin; zero new trusted LOC. Promote to sealed only if a preregistered codec checksum bench shows the library form losing >=3% to a fused reduce.
  - Platform: None — inherits for_chunks.
- **[threads-par] thread-local storage** — CUT
  - Consumer: NONE user-visible (allocator TLS is runtime-internal)
  - Contract: Replacement AMENDED to cover the off-pool consumer (resolves worker_index major): pool code uses worker_index()-addressed arrays; thread-per-connection servers pass a slot index into the closure at spawn, recycled via a checked-library free list — both at par (one indexed load). Reinstatement trigger RE-SCOPED: >=5% measured overhead vs native TLS in EITHER the pool-indexed OR the thread-per-conn slot-indexed case, or detached spawn ever reinstated.
  - Platform: Cut avoids TLS destructor-ordering and dlopen divergence between macOS dyld and glibc — a large verification cost avoided.
- **[threads-par] sleep (threads-par spelling)** — MERGE
  - Consumer: same consumers, served by the single os.sleep row
  - Contract: Row deleted; os.sleep is the one spelling (resolves the duplicate-row minor). Ruling settled here: os.sleep stays sealed even if the condvar surface ships timed wait — timed wait does not cover the no-lock case, so the threads-par audit's demote-to-sugar note is overruled.
  - Platform: n/a — see os.sleep.
- **[threads-par] yield** — CUT
  - Consumer: NONE — spin backoff lives inside the sealed mutex and internal deque
  - Contract: sched_yield semantics are unspecified and invite user spin loops competing with kept sync members. Reinstate only if a user-level wait loop beats kept sync primitives by >=5% and needs yield for fairness — expected never.
  - Platform: sched_yield behavior differs across kernels/schedulers — precisely why it stays internal.
- **[threads-par] thread id / pool worker index** — KEEP
  - Consumer: engines/codecs: per-worker state on the pool via worker-indexed arrays; servers get per-thread state via spawn-time indices (pure user code, no row needed)
  - Contract: AMENDED (resolves off-pool major): worker_index() -> usize < pool_size is typed as available ONLY inside pool task bodies (for_chunks/fork-join) — off-pool use is a checker-rejected context, not a runtime error; scoped thread-per-conn code passes an explicit index into the closure at spawn instead. thread id = opaque u64 unique for process lifetime (synthesized, not gettid); no failure channel; ~trivial trusted LOC.
  - Platform: None — ids synthesized in the runtime, not read from the OS.
- **[threads-par] thread naming** — DEFER
  - Consumer: NONE (debuggability nicety, no performance claim)
  - Contract: Would be: set_name at spawn, best-effort, truncated, no error channel.
  - Platform: pthread_setname_np diverges: macOS self-only 1-arg, Linux 2-arg with 15-byte cap — a different contract per platform for zero scenario value.
- **[threads-par] panic-across-thread semantics** — KEEP
  - Consumer: every concurrent scenario (semantic rule, zero new trusted LOC)
  - Contract: Trap on any thread = immediate whole-process abort; no cross-thread unwinding, no lock poisoning, no observation channel — join never reports 'child trapped' because the process is already gone.
  - Platform: None — abort delivery identical on both platforms.
- **[threads-par] scheduler internals (Chase-Lev deque)** — KEEP
  - Consumer: internal-only: implements fork-join and for_chunks scheduling; no D16 sealed-member row spent
  - Contract: Per-worker deque, owner push/pop, thief steal; no public API; pool shutdown drains queues before joining workers; carries its own memory-ordering proof through the acceptance battery (it is trusted LOC).
  - Platform: Classic Chase-Lev fence bugs are invisible on x86-64 TSO and manifest on arm64 — run adversarial concurrency tests on the arm64 dev machine as the primary bed.
- **[threads-par] blocking-call integration (escape hatch for IO in par bodies)** — DEFER
  - Consumer: NONE in v1 — card rule stands: no blocking calls in par bodies; blocking IO lives on scoped threads feeding the pool via conc_queue
  - Contract: Would be: block_in_place-style hatch retiring the current worker and spawning a replacement; err on spawn failure; replacement joins at pool drop.
  - Platform: None material; the hatch itself is platform-neutral.
- **[threads-par] barrier/latch primitives** — CUT
  - Consumer: NONE as sealed members — engine frame sync served by a checked-library barrier over kept counter+mutex+condvar at par (waits are microsecond-to-millisecond scale)
  - Contract: Library form: latch = counter with condvar wake at zero; barrier = two-phase latch; zero new trusted LOC. Reinstate as sealed if a preregistered engine scenario measures >=5% frame-time regression vs a native futex barrier on the deploy target.
  - Platform: None — inherits the sync members' already-adjudicated futex/ulock divergence.
- **[threads-par] scope cancellation** — CUT
  - Consumer: NONE — server request-timeout served by cooperative flag polling via publish-snapshot-cell, at par, zero trusted LOC; blocked-in-IO release served by net_shutdown(RD) and timed accept
  - Contract: Cooperative library form: shared cancel flag checked at chunk/task boundaries; forced cancellation of a blocked thread rides the evring reinstatement trigger — adjudicate together with evring, never before.
  - Platform: Cut avoids the pthread_cancel/signal cancellation-point swamp (macOS vs Linux).
- **[net] tcp_connect** — KEEP
  - Consumer: network sockets, TCP client leg: DB clients, servers dialing upstreams (51-map request-path scenarios)
  - Contract: socket()+connect() merged: blocking connect to (ip,port) -> linear tcp_stream or errno-class error (ECONNREFUSED/ETIMEDOUT/ENETUNREACH); OS-default SYN timeout; AMENDED: the missing caller deadline is now an explicit named clause of the readiness_wait defer trigger (minutes-long SYN timeout is documented as not-at-par for production clients until that trigger fires); teardown = close via handle drop.
  - Platform: Low. SIGPIPE handled by the runtime's unconditional startup SIGPIPE=IGN invariant (Darwin SO_NOSIGPIPE may still be set defensively); SOCK_CLOEXEC atomic on Linux, fcntl window on macOS (dev-only exposure).
- **[net] tcp_listen** — KEEP
  - Consumer: network sockets: server accept side (51-map server scenarios)
  - Contract: socket()+bind()+listen() merged: (ip,port,backlog,reuseaddr) -> linear tcp_listener or errno error (EADDRINUSE/EACCES). AMENDED teardown (resolves accept-drain major): the unportable 'shutdown-then-close' clause is DELETED (shutdown on a listener is ENOTCONN on macOS); close frees the fd and wakes no blocked acceptor; the specified graceful-drain mechanism is timed accept — SO_RCVTIMEO typed on the listener via sockopt_set — polled against termination_requested().
  - Platform: Backlog clamping differs (somaxconn); SO_REUSEADDR laxer on macOS — Linux (deploy) semantics normative. Darwin accept-honors-SO_RCVTIMEO must be verified in the battery (see open flags); fallback is the loopback self-connect wake pattern in the card, zero new rows.
- **[net] tcp_accept** — KEEP
  - Consumer: network sockets: thread-per-connection server loop (the v1 server architecture with evring deferred)
  - Contract: Blocking accept on shared<tcp_listener> -> (linear tcp_stream, peer_addr) or errno error; ECONNABORTED retried internally, EMFILE/ENFILE surfaced; AMENDED: when the listener's SO_RCVTIMEO fires, accept returns a timeout error value — this is the specified portable drain/poll mechanism; per-stream teardown independent of listener.
  - Platform: accept4(SOCK_CLOEXEC) on Linux vs accept+fcntl on macOS; Darwin inherited-O_NONBLOCK quirk hidden inside the row; Linux accept-honors-SO_RCVTIMEO is documented, Darwin pinned by battery test.
- **[net] socket_raw / bind_raw / listen_raw** — MERGE
  - Consumer: NONE standalone — every consumer wants the composed handle
  - Contract: Folded into tcp_connect, tcp_listen, udp_bind; a bare fd with no role has no checked contract, so it never exists as a value. Reinstate only if a socket type outside {TCP, UDP} is admitted (e.g. unix-domain), and then as its own composed row.
  - Platform: None (removed surface).
- **[net] net_recv (stream read)** — MERGE
  - Consumer: network sockets: request parsing in thread-per-conn servers
  - Contract: Merged into the kept io-file read row: blocking read on fd-backed byte stream -> 0..n bytes, 0 = EOF/peer-FIN, EINTR per the io row's policy, ECONNRESET as errno error, SO_RCVTIMEO expiry mapped to a timeout error value; one read row, one contract, two handle kinds. Split back only if the io read row's verified contract proves incompatible with the timeout channel during the battery.
  - Platform: Low — read(2) is the portable part of sockets; only the errno set widens.
- **[net] net_send (stream write)** — MERGE
  - Consumer: network sockets: response emission — served by the io-file write row on socket handles
  - Contract: FLIPPED KEEP->MERGE (resolves voided-rationale major): with the runtime's unconditional startup SIGPIPE=IGN invariant (see os.signal_term_flag), plain write(2) on a socket returns EPIPE-as-error on both platforms — exactly the io write row's contract, so the audited non-merge reason ('a merged row could not hide the SIGPIPE divergence') is false in context. Socket handles widen the io write row's errno set (EPIPE/ECONNRESET; SO_SNDTIMEO expiry -> timeout error); partial-write count contract identical; teardown = shutdown(WR)+close.
  - Platform: The merge depends on SIGPIPE=IGN being a sealed, unconditional runtime-startup invariant, not opt-in — pinned in the runtime-startup spec; the io write row's battery must exercise socket handles (see open flags).
- **[net] net_sendv (writev gather)** — KEEP
  - Consumer: network sockets: header+body response assembly; par unreachable without it (extra copy or two syscalls interacting with Nagle)
  - Contract: Sole socket-specific emit row after the net_send merge. AMENDED: plain writev on both platforms under the startup SIGPIPE=IGN invariant (MSG_NOSIGNAL branch deleted); gather-send with partial-write contract (total bytes consumed across iovecs); errno channel identical to the merged write row. readv counterpart stays out; trigger = a codec/server scenario showing a measured receive-path copy >5% of request cost.
  - Platform: Low. IOV_MAX 1024 on both in practice.
- **[net] net_shutdown** — KEEP
  - Consumer: network sockets: half-close for protocol EOF; the blocking-world stream-cancel primitive — shutdown(RD) from a sibling releases a thread parked in blocking read
  - Contract: AMENDED typing made explicit: shutdown(how in {RD,WR,RDWR}) on shared<tcp_stream> ONLY — not typed on listeners (listener drain is the timed-accept contract instead); releases blocked readers/writers with EOF/EPIPE; ENOTCONN after peer-close defined as success; does not free the fd — teardown remains close.
  - Platform: macOS wakes racing readers with 0/EOF where Linux may surface ENOTCONN — contract normalizes both to EOF.
- **[net] net_close** — MERGE
  - Consumer: all socket consumers
  - Contract: Merged into the kept io close/handle-drop row: linear-handle consumption, close(2) once, EINTR-on-close policy inherited (fd dead either way); SO_LINGER deliberately unexposed. Split out only if a kept protocol scenario's correctness requires drained close.
  - Platform: Low; EINTR-on-close divergence already owned by the io close row.
- **[net] sockopt_set (closed enum: TCP_NODELAY, SO_REUSEADDR, SO_RCVBUF, SO_SNDBUF, SO_RCVTIMEO, SO_SNDTIMEO)** — KEEP
  - Consumer: network sockets: NODELAY for latency par; REUSEADDR for restart; buffer sizes for throughput par; RCV/SND timeouts load-bearing for thread-per-conn deadlines; AMENDED: listener SO_RCVTIMEO is the graceful-drain mechanism
  - Contract: Typed setter per enum member (no generic setsockopt, no getsockopt in v1); AMENDED typing: SO_RCVTIMEO is additionally typed on tcp_listener, where it bounds accept (timeout error value) — the drain path for signal_term_flag shutdown; kernel-clamped values accepted silently per option contract; excluded by name: SO_REUSEPORT, SO_KEEPALIVE, SO_LINGER, TCP_CORK/NOPUSH (each with its audited trigger).
  - Platform: MATERIAL on buffers: Linux doubles and clamps SO_RCVBUF/SNDBUF to rmem_max/wmem_max, Darwin does not — contract says 'hint, kernel-clamped', never 'exact'. Darwin accept+SO_RCVTIMEO is a mandatory battery item (open flag).
- **[net] readiness_wait (kqueue/epoll)** — DEFER
  - Consumer: readiness/completion multiplexing — already the deferred evring row's scenario; v1 servers are thread-per-connection
  - Contract: If reinstated: register fd set, blocking wait -> ready subset, level-triggered only; deregister-on-close defined against the close row. Trigger AMENDED with a third clause covering connect deadlines (see deferred_with_triggers).
  - Platform: HIGH divergence (kqueue vs epoll registration, edge/level defaults, closed-fd error reporting) — a portable sealed contract is real design work paid twice if evring later subsumes it; on firing, re-evaluate un-deferring evring first.
- **[net] dns_resolve (getaddrinfo)** — DEFER
  - Consumer: NONE at v1 — request-path scenarios connect to config-provided numeric endpoints
  - Contract: Deferred with a 'resolve via OS' card: v1 takes numeric ip:port (address parsing is pure checked code); getaddrinfo drags NSS/dlopen/mDNSResponder into trusted surface and blocks unboundedly — worst battery cost in the unit.
  - Platform: HIGH: macOS resolves via mDNSResponder, Linux via nsswitch/resolv.conf — same call, materially different behavior between dev and deploy.
- **[net] tls** — CUT
  - Consumer: NONE — no v1 demand-map scenario names TLS; fails D16's first prong too
  - Contract: TLS is pure computation over the kept stream rows — ordinary users CAN implement it from primitives + checked libraries, so it is a future checked library, never a sealed row. Reopen only as a checked library when a scenario names it; 'library crypto at par' is a CPU-intrinsics question filed against a future intrinsics unit.
  - Platform: n/a (no row).
- **[net] udp_bind** — KEEP
  - Consumer: network sockets, UDP leg: engines' realtime channels, telemetry, DNS-shaped services — to be pinned to numbered 51-map scenarios before ratification (open flag); also consumed by the deferred stub-resolver path
  - Contract: socket(DGRAM)+bind merged: (ip,port; 0 = ephemeral) -> linear udp_socket or errno error; optional connect(peer) variant for fixed-peer filtering + ECONNREFUSED delivery; teardown = close via handle drop.
  - Platform: Low; ICMP-error surfacing on connected UDP reliable on Linux, best-effort on Darwin — contract marks it advisory.
- **[net] udp_sendto** — KEEP
  - Consumer: network sockets, UDP leg (as udp_bind; scenario pinning pending)
  - Contract: Blocking sendto(buf, addr): whole datagram sent or errno error (EMSGSIZE oversize, EAGAIN on SO_SNDTIMEO) — never partial, by datagram semantics; no SIGPIPE channel; teardown shared with udp_socket.
  - Platform: Low; max datagram size and default sndbuf differ — contract exposes EMSGSIZE rather than a constant.
- **[net] udp_recvfrom** — KEEP
  - Consumer: network sockets, UDP leg (as udp_bind; scenario pinning pending)
  - Contract: Blocking recvfrom(buf) -> (n, peer_addr, truncated: bool) or errno error (EAGAIN on SO_RCVTIMEO); oversize datagram delivered truncated with flag set, remainder discarded — the flag is the portable contract; true-length-on-truncation reinstates only for a named consumer accepting a Linux-only note.
  - Platform: MATERIAL, hence bool-only: Linux MSG_TRUNC reports true length, Darwin only flags — row exposes the intersection so dev and deploy behave identically.
- **[net] sendfile-class zero-copy transmit** — DEFER
  - Consumer: NONE named yet — static-file server is the plausible consumer; v1 pays one extra copy via map_file_ro/read + write
  - Contract: NEW ROW (resolves unpriced-absence minor): would be transmit(io_file_handle range -> socket) with partial-progress contract; not built now — the extra copy is priced as acceptable at v1 scale.
  - Platform: Darwin sendfile differs from Linux in signature and semantics — Linux-normative if reinstated; another reason to defer.
- **[filemap] filemap.map_file_ro** — KEEP
  - Consumer: read-a-big-index (database immutable index/SSTable; compiler large object/archive inputs)
  - Contract: map(io_file_handle, offset, len) -> RoMap owning a fixed-length read-only byte view; ONLY the length is a trusted fact (fixed at map time); AMENDED: len now has a source — the new os.fstat row (fstat-then-map is the stated idiom), closing the audit's unsatisfiable-parameter hole; mapped bytes never margined, every content-derived check non-elidable; error result at map time; touching an externally truncated page = SIGBUS -> process abort; restricted to non-O_DIRECT handles; teardown = munmap on drop, infallible. AMENDED consumer-scope note: request-addressable served files must use read-copy — external truncation is a remotely-triggerable whole-process abort; maps are for process-owned immutable files only.
  - Platform: 16KB pages on macOS arm64 vs 4KB on Linux x86-64 — rounding page-size-parametric, never hardcoded; SIGBUS-on-truncation aborts on both.
- **[filemap] filemap.unmap** — MERGE
  - Consumer: same as map_file_ro
  - Contract: Not a separate row: unmap IS RoMap teardown (drop = munmap, infallible); no early-unmap-while-borrowed possible because the byte view borrows the RoMap.
  - Platform: None beyond the map row.
- **[filemap] filemap.madvise_subset** — DEFER
  - Consumer: NONE (pure perf hint; read-a-big-index functionally complete without it)
  - Contract: Would be: advise(RoMap, range, {sequential|willneed|dontneed-cold}), hint-only, infallible, no teardown — safe to defer because it cannot change observable behavior.
  - Platform: High divergence: macOS lacks/reinterprets several Linux advices (MADV_FREE vs MADV_DONTNEED); hints tuned on Apple Silicon may be no-ops or pessimizations on Linux x86-64.
- **[filemap] filemap.map_file_private_rw** — DEFER
  - Consumer: NONE named in v1 (nearest: linker patch-in-place; pread-into-owned-buffer is the par baseline)
  - Contract: Would be: COW private writable mapping; inherits the full non-elidable-content discipline plus a mixed clean/dirty-page model — highest-complexity mmap row for zero named demand.
  - Platform: COW fault cost and overcommit behavior differ (Linux heuristics vs macOS compressor); 16K vs 4K pages change dirty amplification 4x.
- **[filemap] filemap.map_file_shared_rw** — CUT
  - Consumer: NONE
  - Contract: Ratified v1 non-goal restated: shared writable mappings make every store a cross-process visible effect with no failure channel and unfixable fact-forgery/ordering semantics; WAL durability uses pwrite+fdatasync rows.
  - Platform: Would be severe (msync, unified buffer cache differences); moot when cut.
- **[os] os.proc_spawn** — KEEP
  - Consumer: compiler driver (assembler/linker/sub-tools); build-tool scenarios in the 51-map
  - Contract: spawn(program_path, argv, env = inherit|explicit_list, stdio each of {inherit|null|pipe|io_file_handle}) -> Child via posix_spawn-class primitive; NO pre-exec hook, no fork exposure; AMENDED (resolves SIGPIPE-inheritance major): the child's signal state is reset — POSIX_SPAWN_SETSIGDEF restores default dispositions for all catchable signals (including the runtime's SIGPIPE=IGN) and POSIX_SPAWN_SETSIGMASK empties the mask, so spawned pipeline tools die on SIGPIPE as Unix expects; errors ENOENT/EACCES/EAGAIN as error result; teardown: Child must be consumed by proc_wait (dropping un-waited Child is a checker error).
  - Platform: CORRECTED (stale-claim minor): glibc >=2.24 posix_spawn uses clone(CLONE_VM|CLONE_VFORK) with no page-table copy — spawn latency is comparable on both platforms; the old ~10x large-RSS claim is wrong and must not inform benchmarks. Wired surface stays argv/env/stdio+sigdefault, which is portable.
- **[os] os.proc_wait** — KEEP
  - Consumer: compiler driver (exit codes gate pipeline steps); build-tool interrupt path (grace polling)
  - Contract: wait(Child) -> {exit_code(u8)} | {terminated_by_signal(n)}, blocking, EINTR retried; consumes the linear Child (exactly one reap). AMENDED (resolves child-teardown major, same row/battery): adds try_wait(Child) -> Either<Child, status> via WNOHANG — returns the handle back if still running, consumes it if exited, preserving linearity; kill(TERM) + try_wait/sleep grace loop + kill(KILL) is the specified deadline pattern.
  - Platform: Low; wait-status encoding identical in practice; row reports raw signal number plus a portable enum for TERM/KILL/SEGV.
- **[os] os.proc_kill** — KEEP
  - Consumer: build tool Ctrl-C propagation and hung-child recovery (NEW ROW resolving the no-kill major): on termination_requested(), parent kills children with TERM, graces via try_wait, escalates to KILL, then waits — matching make's interrupt behavior
  - Contract: kill(&Child, sig in {TERM, KILL}) -> ok | err(EPERM); borrows, does not consume or reap — the Child is still owed its wait, so no zombie and no double-reap; ESRCH unreachable while the linear handle is live (child may be a zombie but the pid is not recycled before reap).
  - Platform: kill(2) identical on both platforms; ~30 trusted LOC.
- **[os] os.time** — KEEP
  - Consumer: servers (timeouts/deadlines), databases (WAL timestamps), engines (frame pacing) — broadest consumer set in the map
  - Contract: monotonic_ns() -> u64 never-decreasing since arbitrary epoch, and wall_ns() -> unix epoch ns; both infallible, vDSO/commpage cost; monotonic PINNED to exclude-suspend semantics on both OSes.
  - Platform: MATERIAL: Linux CLOCK_MONOTONIC excludes suspend, macOS includes it — implement via CLOCK_UPTIME_RAW on macOS to honor the pin; flagged in the acceptance battery.
- **[os] os.sleep** — KEEP
  - Consumer: servers (retry/backoff), benchmark harnesses, proc_wait grace loops; the single sleep spelling after the threads-par duplicate merged here
  - Contract: sleep(duration) blocks at-least the requested monotonic duration (may oversleep, never wakes early); EINTR retried internally so infallible; no teardown. RULING (resolves cross-unit minor): stays sealed even if the condvar surface ships timed wait — timed wait does not cover the no-lock case; one row, one battery.
  - Platform: macOS timer coalescing/App Nap oversleeps more aggressively than Linux; the at-least contract absorbs it — perf-doc note, not semantics.
- **[os] os.env_get** — KEEP
  - Consumer: servers/databases reading deployment config (PORT, data dir) — standard container input channel
  - Contract: env_get(name) -> Option<owned bytes> (not guaranteed UTF-8); race-free BY CONSTRUCTION because no setenv row exists anywhere (environ immutable post-start); no teardown.
  - Platform: None material.
- **[os] os.env_set** — CUT
  - Consumer: NONE (child env set explicitly through proc_spawn's env list)
  - Contract: Cut precisely to keep env_get race-free; setenv is process-global mutable state with documented races in every libc.
  - Platform: Moot.
- **[os] os.args** — KEEP
  - Consumer: compilers and every CLI-shaped scenario in the map
  - Contract: args() -> immutable snapshot slice of argv as byte strings (argv[0] included, no UTF-8 guarantee); infallible, captured at process start.
  - Platform: None.
- **[os] os.random_csprng** — KEEP
  - Consumer: hash-map seed (hashbrown-class DoS resistance), servers (tokens), databases (WAL/journal salts)
  - Contract: fill_random(&uniq buf) fills the whole buffer with getentropy-class CSPRNG bytes, looping over the 256-byte cap; unrecoverable entropy failure -> abort (fail-closed, no weak fallback); NOT a fact channel.
  - Platform: getentropy on both (macOS >=10.12, glibc >=2.25); 256-byte cap identical; low.
- **[os] os.exit** — KEEP
  - Consumer: compilers (exit codes are the driver protocol); every CLI scenario
  - Contract: exit(code: u8) -> ! terminates without unwinding, drop glue, or ANY user-space flushing — AMENDED (resolves flush-contradiction major): the 'flushes sealed stdio sinks' clause is DELETED because the sealed stdio layer is unbuffered (nothing to flush); checked-library buffered writers MUST be explicitly flushed before exit, and the library provides an exit-with-flush wrapper as the documented pattern for compilers using buffered stdout.
  - Platform: None.
- **[os] os.abort** — MERGE
  - Consumer: already consumed by trap semantics (trap = process abort, ratified)
  - Contract: Not a new row: user-callable abort is the already-decided trap mechanism spelled once; -> !, no failure channel, no cleanup.
  - Platform: None.
- **[os] os.signal_term_flag** — KEEP
  - Consumer: server graceful shutdown (drain via timed accept + per-stream RCVTIMEO, fdatasync WAL, exit); sigaction unreachable from primitives
  - Contract: termination_requested() -> bool polling a sticky flag set by a runtime-installed SIGTERM/SIGINT handler that only stores to that flag (zero user code in signal context); AMENDED (pins the net-merge dependency): SIGPIPE=IGN and the sticky-flag handler are installed UNCONDITIONALLY at runtime startup as a sealed invariant — independent of whether this API is ever called — because the merged io write row's socket EPIPE contract depends on it; proc_spawn resets dispositions in children so the invariant never leaks across exec.
  - Platform: sigaction semantics equivalent for this shape on both OSes; low.
- **[os] os.signals_general** — DEFER
  - Consumer: NONE (no v1 scenario needs dispositions beyond TERM/INT-as-flag and PIPE-as-ignore)
  - Contract: Would be additional sticky flags only, never user handlers (arbitrary handlers reintroduce async-signal-safety obligations contradicting the sealed-trust budget).
  - Platform: Signal numbering/realtime-signal availability differ (SIGRTMIN absent on macOS) — another reason to defer.
- **[os] os.cwd_get** — DEFER
  - Consumer: NONE (kernel resolves relative paths against cwd for free; no v1 scenario materializes the cwd string)
  - Contract: Would be: cwd() -> owned path bytes, error on unlinked-cwd edges; read-only if reinstated (chdir stays cut), so race-free.
  - Platform: Low (PATH_MAX handling differs slightly).
- **[os] os.chdir** — CUT
  - Consumer: NONE
  - Contract: Process-global mutable state silently changing every concurrent relative open — the interference class the language excludes; pass absolute or deliberately-relative paths instead; a future openat/dir-handle row is the admissible replacement if per-directory scoping is demanded.
  - Platform: Moot.
- **[os] os.path_manipulation** — CUT
  - Consumer: NONE as a sealed row (compilers consume it from a checked library)
  - Contract: join/basename/extension are pure byte-string computation — implementable at par from primitives, so D16's first prong excludes them; checked library, zero trust budget.
  - Platform: None (both targets POSIX; no drive letters).
- **[os] os.stdio_handles** — MERGE
  - Consumer: compilers (diagnostics to stderr), every CLI/server scenario (logs)
  - Contract: stdout/stderr/stdin are the three pre-opened io-file handles (fd 0/1/2) exposed by accessors, reusing io-file read/write rows verbatim (short-write/EPIPE-as-error, EINTR retried); UNBUFFERED at the sealed layer — AMENDED for consistency with os.exit: nothing flushes at process end; line/block buffering is a checked library whose flush is explicit (exit-with-flush wrapper is the documented pattern).
  - Platform: None material; pipe vs tty vs file identical across targets at this layer.
- **[os] fs.fstat (handle-based stat)** — KEEP
  - Consumer: NEW ROW (resolves the FATAL): read-a-big-index — the source of map_file_ro's len; static-file server Content-Length; build tool post-open verification; TOCTOU-free spelling
  - Contract: fstat(&io_file_handle) -> {kind: {file|dir|other}, size: u64, mtime_ns: u64} | err(EIO); EBADF unreachable by handle linearity; no teardown; size/mtime are ordinary values, not optimizer facts (the file can change; only map_file_ro's map-time len is ever trusted).
  - Platform: st_mtim vs st_mtimespec naming sealed; mtime granularity is filesystem-dependent (APFS/ext4 ns, older fs coarser) — contract exposes ns field with a granularity caveat, no equality-across-filesystems claim.
- **[os] fs.stat_path** — KEEP
  - Consumer: NEW ROW (resolves the FATAL): build tool mtime-based staleness at par with make/ninja (one syscall per path — open+fstat+close would triple the metadata-scan syscall count); recursive grep entry classification and symlink-loop avoidance
  - Contract: stat(path, follow: bool) -> {kind: {file|dir|symlink|other}, size, mtime_ns} | err(ENOENT/EACCES/ELOOP); follow=false is lstat (symlink itself); inherently TOCTOU-racy by nature — contract states results are advisory snapshots, and correctness-critical reads must open-then-fstat.
  - Platform: Same struct divergences as fstat, sealed; ELOOP limits differ slightly — contract exposes the error, not the limit.
- **[os] fs.readdir** — KEEP
  - Consumer: NEW ROW (resolves the FATAL): recursive parallel grep tree walk; build tool source globbing
  - Contract: opendir(path) -> DirStream | err; next(&uniq DirStream) -> Option<{name: owned bytes, kind_hint: {file|dir|symlink|unknown}}>; '.' and '..' excluded; NO ordering guarantee; entries under concurrent modification may be missed or duplicated (POSIX reality, stated); kind_hint is advisory (d_type may be unknown) — confirm via stat_path; teardown = closedir on drop, infallible.
  - Platform: getdents64 vs getdirentries64 sealed; d_type population differs by filesystem on both OSes — hence the unknown fallback in the contract.
- **[os] fs.mkdir** — KEEP
  - Consumer: NEW ROW (resolves the FATAL): build tool output-directory creation
  - Contract: mkdir(path) -> ok | err(EEXIST/ENOENT/EACCES); mode 0o777 & ~umask; single level only — mkdir-p is a checked-library loop over this row (EEXIST surfaced so the loop is race-tolerant); no teardown.
  - Platform: None material; identical on both targets.
- **[os] fs.remove (unlink + rmdir-empty, typed kind)** — KEEP
  - Consumer: NEW ROW (resolves the unlink MAJOR): KV-store compaction reclaiming dead SSTable/WAL-segment files — a correctness requirement (disk usage otherwise grows without bound); build tool clean step
  - Contract: remove(path, kind: {file, empty_dir}) -> ok | err(ENOENT/EACCES/ENOTEMPTY/kind-mismatch), mapping to unlink/rmdir under one contract and one battery; POSIX unlink-while-open keeps data reachable until last close on both platforms (compaction can unlink files still mapped/read by in-flight queries); recursive tree removal is a checked-library walk over readdir+remove.
  - Platform: Low; unlink-while-open semantics POSIX-conformant on both; errno for kind-mismatch differs (EISDIR/EPERM) — normalized by the row.
- **[os] io.ftruncate** — KEEP
  - Consumer: NEW ROW (resolves the ftruncate MAJOR): WAL segment recycling and KV compaction space reclaim; formally extends the pre-decided io-file list ('plus what wal needs') and must be verified before wal ratification
  - Contract: ftruncate(&write-opened io_file_handle, len) -> ok | err(EINVAL/EIO/EFBIG); shrink discards beyond len, extend reads back as logical zeros; no physical-allocation claim (sparseness fs-dependent); durability of the size change still requires the kept fdatasync row; no teardown.
  - Platform: Both support shrink and extend; APFS vs ext4 sparse/preallocation behavior differs — contract is logical-content-only, so no divergence surfaces.

## Five-program composition walk (attack evidence)

- Static-file web server: tcp_listen(reuseaddr) -> tcp_accept on shared<tcp_listener> -> scoped spawn per connection inside a long-lived scope (spawn EAGAIN gives a 503/close path) -> sockopt {TCP_NODELAY, SO_RCVTIMEO, SO_SNDTIMEO} -> request bytes via the merged io read row -> path join/sanitize as a pure checked library -> io-file open -> response via net_sendv (headers+body) with partial-write resume, or map_file_ro + net_send -> net_shutdown(WR) half-close -> drop-close -> signal_term_flag + per-stream RCVTIMEO for handler drain -> os.exit. BREAKS: (a) no fstat, so Content-Length and map_file_ro's len have no source except reading the whole file first — kills the mmap fast path (chunked encoding is a protocol downgrade, not par); (b) graceful drain cannot portably wake the thread blocked in accept (shutdown-on-listener is ENOTCONN on macOS, net_shutdown is not typed on listeners) — as specified, the accept thread parks forever and only a cleanup-skipping exit() escapes; (c) minor: one extra copy vs sendfile, and SIGBUS-abort exposure if serving from maps that others can truncate. Writable, but not at par on the metadata path, and shutdown is broken-as-specified on the dev platform.
- Build tool: args + env_get -> manifest via io read -> dependency graph in checked containers -> N scoped worker threads + conc_queue (mpmc) of ready jobs — correctly avoiding par fork-join since jobs block, so the no-blocking card and the deferred blocking-hatch are mutually consistent here -> proc_spawn(argv, explicit env, stdio=pipe) -> pipe drain on scoped threads -> proc_wait exit codes gate dependents -> outputs published via write + fsync + rename + dir-fsync -> diagnostics on merged stderr -> os.exit code. BREAKS FATAL: no stat/mtime means incremental builds are impossible at par (full content re-hash of the tree every run); no mkdir means output directories cannot be created at all; no unlink means no clean step; no child kill means Ctrl-C orphans running compilers; spawned tools inherit SIGPIPE=IGN and can misbehave in pipelines. The scheduling/execution core is fully served by kept rows; the unowned filesystem-metadata seam is what breaks the program.
- LZ4 CLI: args -> input via io-file open + read loop (or the stdin fd0 accessor) into an owned growable buffer -> pool(n=0 default cores) -> par.for_chunks over frame-sized blocks for parallel compression (checker-proved disjoint &uniq chunks are exactly the needed shape; compression itself is pure checked code) -> checksums via the merged par.reduce library form (wrapping-int monoid, order-insensitive) -> output via io write with short-write loop -> exit(0/1). PASSES at par with only the kept rows. Residuals: no fstat means no input-size preallocation (streaming append is fine and par holds), and the reduce library needs a chunk-index/output-slot facility that the for_chunks sketch does not yet state.
- KV store with WAL: serving via tcp_listen/tcp_accept, thread-per-conn scoped spawns with SO_RCVTIMEO deadlines, net_send/net_sendv responses, net_shutdown(RD) as the cross-thread cancel; state via shared<T> + mutex + publish-snapshot-cell memtable and conc_queue to background flush/compaction threads; random_csprng for hash seeds; durability via pwrite + fdatasync WAL, checkpoint = write-new + fsync + rename + dir-fsync (all pre-decided io rows); recovery reads the WAL to EOF via a pread loop (read 0 = EOF), so the missing stat is survivable there; SSTable reads via map_file_ro; shutdown via signal_term_flag -> drain -> final fdatasync -> exit. BREAKS: compaction cannot reclaim space — no unlink/ftruncate anywhere, so disk usage grows without bound (a workload failure, not a perf shortfall); map_file_ro len again needs fstat or an O(file) startup probe; the blocked-accept wakeup hole is shared with the web server; and dev-machine durability testing is void without an F_FULLFSYNC pin in the io rows. Everything else runs at par on kept rows.
- Parallel grep: args (pattern + explicit file list) -> io-file open per file -> read loop into a buffer (the mmap path is blocked by the fstat-len gap, but read-based scanning is GNU grep's own approach, so par holds) -> pool + conc_queue (mpmc) of files, par.for_chunks within large files with chunk-boundary straddle handling in the pure matcher -> matches serialized to stdout under mutex via the merged stdio write row -> exit code from a shared counter. BREAKS FATAL in its normal form: recursive grep over a directory tree is unwritable — no readdir and no stat to classify entries. Fed an external file list (find | xargs style) it passes at par; early-exit modes (-q/-l) over-scan only within one chunk, since cooperative cancellation via publish-snapshot-cell between chunks is available — acceptable.

## Deferred with triggers

- threads-par / worker-pool pinning-affinity-priorities: fires when a named engine or server scenario measures >=5% throughput or p99-latency improvement from pinning on the Linux x86-64 deployment target, with the benchmark preregistered before the API is designed.
- threads-par / thread naming: fires at the first debugging session against the Linux deployment target where anonymous threads materially slow diagnosis; reinstatement cost ~20 trusted LOC.
- threads-par / blocking-call integration (par-body IO hatch): fires when the build-system fork-join scenario shows >=10% end-to-end throughput loss or structural impossibility restructuring IO onto dedicated scoped IO threads vs an in-body hatch, measured on the deployment target.
- net / readiness_wait (kqueue-epoll), trigger AMENDED with a third clause: fires when (a) a named demand-map scenario requires >10,000 concurrent mostly-idle connections per process, or (b) thread-per-conn at a kept scenario's concurrency measures >1.3x worse p99 latency or >2x RSS than an epoll reference on Linux x86-64, or (c) NEW: a kept client scenario requires a connect deadline materially shorter than the OS SYN timeout (~75s macOS / ~2min Linux) — the tcp_connect deadline gap explicitly rides this clause. On firing, first re-evaluate un-deferring evring (completion model, one surface); add readiness only if the evring trigger has independently not fired.
- net / dns_resolve: fires when a kept scenario must resolve names at runtime — an outbound HTTP/RPC client scenario is admitted to the demand map, or a kept DB-client scenario's endpoints demonstrably cannot be fixed as numeric addresses in config; reinstate as sealed blocking getaddrinfo with an explicit no-deadline caveat, or as a checked-library stub resolver over the kept UDP rows if par allows.
- net / sendfile-class zero-copy transmit (NEW row): fires when a preregistered static-file-server benchmark on Linux x86-64 shows >=10% throughput loss or >=15% CPU cost from the map_file_ro/read+write extra copy vs a sendfile reference at the scenario's file-size mix.
- filemap / madvise_subset: fires when the pinned read-a-big-index benchmark on Linux x86-64 shows >=10% wall-time or >=20% major-fault improvement from MADV_SEQUENTIAL/WILLNEED over default readahead; reinstate only the advice values that cleared the bar.
- filemap / map_file_private_rw: fires when a named scenario (e.g. linker relocating a mapped input) shows the pread-copy baseline >=1.3x slower end-to-end or >=2x peak RSS on a pinned Linux x86-64 workload.
- os / signals_general: fires at the first named scenario requiring a signal outside {TERM, INT, PIPE} (e.g. SIGHUP config reload) where a polled flag or an external control channel is shown inadequate; reinstate as additional sticky flags only, never user handlers.
- os / cwd_get: fires at the first scenario that must emit absolute paths into artifacts (compiler dep-files/diagnostics) where requiring absolute-path CLI inputs is demonstrated to break an existing consumer's invocation protocol.

## Open flags

- Darwin accept+SO_RCVTIMEO is now load-bearing (it is the specified graceful-drain mechanism): the acceptance battery MUST verify on the macOS dev machine that accept returns the timeout error when the listener's SO_RCVTIMEO fires; documented fallback if it fails is the loopback self-connect wake pattern in the server card (zero new rows) — until verified, server drain remains unproven on the dev platform.
- F_FULLFSYNC cross-reference (outside these four pockets): the pre-decided io-file fsync/fdatasync rows must pin the Darwin F_FULLFSYNC mapping as the durable spelling BEFORE any WAL-durability test on the dev machine counts as evidence — otherwise the battery can go falsely green on exactly the platform where semantics differ most.
- The net_send->io-write merge makes the io write row's contract depend on the runtime's unconditional startup SIGPIPE=IGN invariant: that invariant must be stated in the runtime-startup spec (not only in the signal_term_flag row), and the io write row's battery must exercise socket handles (EPIPE, ECONNRESET, SO_SNDTIMEO timeout).
- for_chunks' new indexed/zipped disjoint out-slot shape is new checker surface that carries borrow facts across threads — it needs its own hostile fact-channel review before the par.reduce library form lands (per the standing rule: fact channels get adversarial review before shipping).
- fs.fstat and io.ftruncate formally extend the pre-decided io-file list ('plus what wal needs'): log the explicit enumeration in decision-gates before wal ratification so that phrase is no longer load-bearing; the whole fs-namespace unit (fstat, stat_path, readdir, mkdir, remove, ftruncate) needs its own five-part acceptance battery pass and a decision-gates line as a new unit audit.
- UDP rows (udp_bind/sendto/recvfrom) keep is conditionally sound but their consumers must be pinned to numbered 51-map scenarios before ratification — currently the loosest D16 second-prong naming in the net unit.
- Owner ratification needed on the sleep ruling: os.sleep remains sealed even if the condvar surface ships timed wait (the no-lock case) — this overrules the threads-par audit's demote-to-sugar note and settles the one-spelling tension; confirm whether the ratified condvar surface includes timed wait at all.
- Re-run the five-programs composition walk against the AMENDED contract text before ratification (build tool and recursive grep should now pass outright; KV compaction reclaims space via fs.remove+io.ftruncate; the web server metadata path is closed by fs.fstat) — the attack demonstrated that unit-isolated audits miss composition seams, so the walk is the ratification gate, not the row list alone.
- Recursive tree deletion and race-robust directory-scoped IO remain checked-library loops over readdir+remove; if a scenario ever needs TOCTOU-robust tree operations, the admissible future shape is an openat/dir-handle unit (also the designated chdir replacement) — no trigger fires today.