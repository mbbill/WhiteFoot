#!/usr/bin/env python3
"""Part A -- exhaustive small-bound model check of the catalog conc_queue SPSC
protocol (optables.md S.3: Lamport ring, pow2 capacity, monotone head/tail,
acquire/release handoff, cursor caching; CG-QOP = no RMW).

Memory model: a release/acquire OPERATIONAL semantics with per-thread views.
  * Each shared location holds an append-only list of writes; a write carries a
    "view" (the writer's knowledge). A release store carries the writer's full
    view; a relaxed store carries only its own coherence. An acquire load imports
    the read message's view into the reader's view; a relaxed load does not.
  * Counter loads (head/tail) read the latest value (coherence); staleness on a
    monotone counter is strictly conservative for SAFETY, so latest is the worst
    case for the properties checked -- this keeps the state space finite and
    avoids spurious relaxed-counter livelock.
  * Slot (data) reads are PLAIN and branch over every coherence-visible message
    (floor..latest, floor = reader's imported view of that slot). Under intact
    release/acquire the floor pins the exact published write; a broken pair
    leaves the floor stale so a pre-publication / stale value is readable.
  * The head (WAR / slot-reuse) pair has NO consumer->producer data, so its
    fence role is pure ordering; each head weakening additionally enables the
    intra-thread reordering it stops forbidding (relaxed head-release: publish
    before read; relaxed head-acquire: overwrite while apparently full).

Bounds: capacity 2, producer sends [1,2,3,4], consumer receives 4. Exhaustive.
"""
import sys

CAP = 2
MASK = CAP - 1
VALS = [1, 2, 3, 4]          # item i has value VALS[i]
NITEMS = len(VALS)
BOT = -1                     # uninitialized slot sentinel

TAIL, HEAD, S0, S1 = 0, 1, 2, 3
NLOC = 4
def slot_of(i): return S0 if (i & MASK) == 0 else S1

# ---- shared memory: per-loc message lists + per-thread views -------------
# msgs: tuple of 4 tuples; each = tuple of (value, view) ; view = 4-tuple ints
# a view entry is the highest message index known for that loc (-1 = none).

def init_mem():
    msgs = (
        ((0, (0, -1, -1, -1)),),      # tail = 0
        ((0, (-1, 0, -1, -1)),),      # head = 0
        ((BOT, (-1, -1, 0, -1)),),    # slot0
        ((BOT, (-1, -1, -1, 0)),),    # slot1
    )
    pv = (0, 0, 0, 0)
    cv = (0, 0, 0, 0)
    return msgs, pv, cv

def store(msgs, view, loc, value, order):
    ni = len(msgs[loc])
    if order == 'release':
        mv = list(view); mv[loc] = ni; mv = tuple(mv)
    else:  # relaxed / plain: carries only its own coherence
        mv = [-1, -1, -1, -1]; mv[loc] = ni; mv = tuple(mv)
    msgs2 = tuple(msgs[k] if k != loc else msgs[k] + ((value, mv),) for k in range(NLOC))
    view2 = tuple(view[k] if k != loc else ni for k in range(NLOC))
    return msgs2, view2

def load_counter(msgs, view, loc, order):
    """Read the latest value (coherence); import the view iff acquire."""
    ni = len(msgs[loc]) - 1
    val, mv = msgs[loc][ni]
    nv = list(view); nv[loc] = ni
    if order == 'acquire':
        for k in range(NLOC):
            if mv[k] > nv[k]:
                nv[k] = mv[k]
    return val, tuple(nv)

def load_slot_branches(msgs, view, loc):
    """PLAIN load: yield (value, view') for every coherence-visible message."""
    floor = view[loc]
    for idx in range(floor, len(msgs[loc])):
        val, _mv = msgs[loc][idx]
        nv = list(view); nv[loc] = idx
        yield val, tuple(nv)

# ---- protocol state and transition ---------------------------------------
# state = (p, ch, wrote, c, ct, readf, pubf, recv, msgs, pv, cv)
#   producer: p items published, ch cached head, wrote = slot written for item p
#   consumer: c items advanced, ct cached tail, readf/pubf for item c, recv tuple

def successors(st, mut):
    (p, ch, wrote, c, ct, readf, pubf, recv, msgs, pv, cv) = st
    order_pt = 'relaxed' if 'tail_rel' in mut else 'release'   # producer publish tail
    order_ct = 'relaxed' if 'tail_acq' in mut else 'acquire'   # consumer refresh tail
    order_ch = 'relaxed' if 'head_rel' in mut else 'release'   # consumer publish head
    order_ph = 'relaxed' if 'head_acq' in mut else 'acquire'   # producer refresh head
    out = []  # list of (label, newstate, violation_or_None)

    # --- producer ---
    inflight = p - ch
    if p < NITEMS and inflight == CAP:                          # appears full -> refresh
        val, pv2 = load_counter(msgs, pv, HEAD, order_ph)
        out.append(('P_refresh', (p, val, wrote, c, ct, readf, pubf, recv, msgs, pv2, cv), None))
    if p < NITEMS and not wrote and (inflight < CAP or 'head_acq' in mut):
        # head_acq weakened: the slot store may reorder before the gating acquire,
        # so it can fire while the slot is still apparently in use.
        msgs2, pv2 = store(msgs, pv, slot_of(p), VALS[p], 'relaxed')
        out.append(('P_write#%d' % p,
                    (p, ch, True, c, ct, readf, pubf, recv, msgs2, pv2, cv), None))
    if p < NITEMS and wrote:
        msgs2, pv2 = store(msgs, pv, TAIL, p + 1, order_pt)     # publish, then advance p
        out.append(('P_publish#%d' % p, (p + 1, ch, False, c, ct, readf, pubf, recv, msgs2, pv2, cv), None))

    # --- consumer ---
    avail = ct - c
    if c < NITEMS and avail == 0:                              # appears empty -> refresh
        val, cv2 = load_counter(msgs, cv, TAIL, order_ct)
        out.append(('C_refresh', (p, ch, wrote, c, val, readf, pubf, recv, msgs, pv, cv2), None))
    if c < NITEMS and not readf and avail > 0:
        for val, cv2 in load_slot_branches(msgs, cv, slot_of(c)):
            viol = None
            if val == BOT:
                viol = 'read-before-published: item %d slot holds BOT' % c
            elif val != VALS[c]:
                viol = 'wrong/duplicated/lost: item %d read %d, expected %d' % (c, val, VALS[c])
            out.append(('C_read#%d=%d' % (c, val),
                        (p, ch, wrote, c, ct, True, pubf, recv + (val,), msgs, pv, cv2), viol))
    if c < NITEMS and not pubf and (readf or 'head_rel' in mut):
        # head_rel weakened: the head release may reorder before the slot read,
        # signalling "slot free" before the value is actually taken.
        msgs2, cv2 = store(msgs, cv, HEAD, c + 1, order_ch)
        out.append(('C_publish#%d' % c, (p, ch, wrote, c, ct, readf, True, recv, msgs2, pv, cv2), None))
    if c < NITEMS and readf and pubf:
        out.append(('C_advance#%d' % c, (p, ch, wrote, c + 1, ct, False, False, recv, msgs, pv, cv), None))

    return out

def terminal(st):
    p, _ch, _w, c, _ct, _r, _pu, _recv = st[0], st[1], st[2], st[3], st[4], st[5], st[6], st[7]
    return p == NITEMS and c == NITEMS

def explore(mut):
    msgs, pv, cv = init_mem()
    start = (0, 0, False, 0, 0, False, False, (), msgs, pv, cv)
    seen = set()
    stack = [start]
    violations = set()     # unique violation descriptions
    deadlocks = 0
    bad_terminals = 0
    good_terminals = 0
    while stack:
        st = stack.pop()
        if st in seen:
            continue
        seen.add(st)
        succ = successors(st, mut)
        if terminal(st):
            if st[7] == tuple(VALS):
                good_terminals += 1
            else:
                bad_terminals += 1
                violations.add('terminal recv=%r != (1,2,3,4)' % (st[7],))
            continue
        if not succ:
            deadlocks += 1
            violations.add('deadlock at non-terminal state p=%d c=%d recv=%r' % (st[0], st[3], st[7]))
            continue
        for _label, nst, viol in succ:
            if viol:
                violations.add(viol)
            stack.append(nst)
    return {
        'states': len(seen),
        'violations': sorted(violations),
        'deadlocks': deadlocks,
        'bad_terminals': bad_terminals,
        'good_terminals': good_terminals,
    }

MUTS = {
    'CORRECT (all acquire/release)': set(),
    'M1 tail publish  release->relaxed': {'tail_rel'},
    'M2 tail read     acquire->relaxed': {'tail_acq'},
    'M3 head publish  release->relaxed': {'head_rel'},
    'M4 head read     acquire->relaxed': {'head_acq'},
}

if __name__ == '__main__':
    print('SPSC exhaustive model check  (cap=%d, items=%r, consumer receives %d)\n'
          % (CAP, VALS, NITEMS))
    for name, mut in MUTS.items():
        r = explore(mut)
        ok = (not r['violations'] and r['deadlocks'] == 0 and r['bad_terminals'] == 0)
        verdict = 'SAFE' if ok else 'VIOLATION FOUND'
        print('%-38s states=%-6d good_term=%-4d bad_term=%-3d deadlock=%-3d  %s'
              % (name, r['states'], r['good_terminals'], r['bad_terminals'],
                 r['deadlocks'], verdict))
        for v in r['violations'][:3]:
            print('        - %s' % v)
        if len(r['violations']) > 3:
            print('        - ... (%d distinct violation classes total)' % len(r['violations']))
    print('\nProperties checked on every reachable state: no lost/duplicated/wrong item,'
          '\nno read-before-published slot, FIFO (terminal recv == (1,2,3,4)), and both'
          '\nthreads terminate (no non-terminal deadlock). Exhaustive over all reachable'
          '\nstates (dedup fixpoint). Mutation leg: each of the 4 acquire/release halves'
          '\nweakened to relaxed one at a time -- all four are caught at this bound.')
