# -*- coding: utf-8 -*-
"""
Eval-1 — Multi-session drift/conflict experiment.

Question: when K concurrent "sessions" (writers) update a SHARED artifact,
does an append-only + id-merge log (B) avoid the lost-updates / corruption
that a naive shared-document read-modify-write (A) incurs?

- Condition A (baseline): each writer reads the whole JSON, applies its change,
  writes the whole JSON back. No lock. (= what an LLM session does if told
  "edit the dashboard file".)
- Condition B (naive append): each writer APPENDS one line {id, key, val} in
  plain "a" mode. Final state = replay + id-merge. Exposes that plain append is
  NOT atomic on every platform (Windows: lseek-to-EOF then write races).
- Condition C (ours): append guarded by a short-lived OS lock (msvcrt/fcntl), so
  every append lands atomically at EOF. This is the discipline the real helper
  must follow to be truly conflict-free.

Each event writes a UNIQUE (id, key) pair, so ground truth is unambiguous:
every event must appear in the final state. Anything missing = a LOST UPDATE.

Honest scope: single machine, simulated concurrency (multiprocessing + jitter),
no real LLM calls (the mechanism under test is the logging discipline, not the model).
Std-lib only. Windows-safe (module-level workers + __main__ guard).
"""
import json, os, time, random, statistics, csv, sys, io, tempfile
import multiprocessing as mp

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------- workload ----------
def make_workload(n_items, evs_per_item, seed):
    rnd = random.Random(seed)
    events = []           # (id, key, val) ; key unique per event
    ground = {}           # id -> {key: val, ...}  (every event applied)
    s = 0
    for i in range(n_items):
        iid = f"T{i:03d}"
        ground[iid] = {"id": iid}
        for _ in range(evs_per_item):
            key = f"k{s}"
            val = s
            events.append((iid, key, val))
            ground[iid][key] = val
            s += 1
    rnd.shuffle(events)   # interleave so writers race on different items too
    return events, ground

def split_round_robin(events, K):
    buckets = [[] for _ in range(K)]
    for idx, e in enumerate(events):
        buckets[idx % K].append(e)
    return buckets

# ---------- Condition A: naive shared JSON, read-modify-write (no lock) ----------
def writerA(args):
    path, my_events, jitter = args
    rnd = random.Random(os.getpid())
    for (iid, key, val) in my_events:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}                       # partial/empty mid-write -> start blank (lossy)
        rec = data.get(iid, {"id": iid})
        rec[key] = val
        data[iid] = rec
        time.sleep(jitter * rnd.random())   # widen the read->write window
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        time.sleep(jitter * rnd.random())

def read_final_A(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), 0
    except Exception:
        return {}, 1                        # final file itself corrupted

# ---------- Condition B: naive append (plain "a" mode) ----------
def writerB(args):
    path, my_events, jitter = args
    rnd = random.Random(os.getpid())
    for (iid, key, val) in my_events:
        line = json.dumps({"id": iid, key: val}, ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")            # NOT atomic on Windows -> can race
        time.sleep(jitter * rnd.random())

# ---------- Condition C: append guarded by short-lived OS lock ----------
def _lock(lf):
    if os.name == "nt":
        import msvcrt
        lf.seek(0)
        msvcrt.locking(lf.fileno(), msvcrt.LK_LOCK, 1)   # blocks/retries ~10s
    else:
        import fcntl
        fcntl.flock(lf, fcntl.LOCK_EX)

def _unlock(lf):
    if os.name == "nt":
        import msvcrt
        lf.seek(0)
        msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(lf, fcntl.LOCK_UN)

def writerC(args):
    path, my_events, jitter = args
    lockpath = path + ".lock"
    rnd = random.Random(os.getpid())
    for (iid, key, val) in my_events:
        line = json.dumps({"id": iid, key: val}, ensure_ascii=False)
        with open(lockpath, "a+") as lf:
            _lock(lf)
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")    # atomic w.r.t. other writers
            finally:
                _unlock(lf)
        time.sleep(jitter * rnd.random())

def replay_B(path):
    state, corrupt = {}, 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                corrupt += 1
                continue
            iid = obj.get("id")
            if not iid:
                corrupt += 1
                continue
            rec = state.setdefault(iid, {"id": iid})
            for k, v in obj.items():
                if k != "id":
                    rec[k] = v
    return state, corrupt

# ---------- scoring ----------
def count_lost(final_state, ground):
    lost = 0
    for iid, grec in ground.items():
        frec = final_state.get(iid, {})
        for k, v in grec.items():
            if k == "id":
                continue
            if frec.get(k) != v:
                lost += 1
    return lost

WORKERS = {"A": writerA, "B": writerB, "C": writerC}

def run_trial(cond, K, events, ground, jitter, tmpdir, trial):
    path = os.path.join(tmpdir, f"shared_{cond}_{K}_{trial}.{'json' if cond=='A' else 'log'}")
    if cond == "A":
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)
    else:
        open(path, "w", encoding="utf-8").close()
    buckets = split_round_robin(events, K)
    args = [(path, b, jitter) for b in buckets]
    with mp.Pool(processes=K) as pool:
        pool.map(WORKERS[cond], args)
    if cond == "A":
        final, file_corrupt = read_final_A(path)
        line_corrupt = 0
    else:
        final, line_corrupt = replay_B(path)
        file_corrupt = 0
    lost = count_lost(final, ground)
    for p in (path, path + ".lock"):
        try: os.remove(p)
        except Exception: pass
    total = sum(len(g) - 1 for g in ground.values())
    return {"lost": lost, "corrupt": file_corrupt + line_corrupt,
            "correct": int(lost == 0 and file_corrupt == 0 and line_corrupt == 0),
            "total_events": total}

def main():
    N_ITEMS, EVS, R, JITTER = 20, 4, 15, 0.0015
    Ks = [2, 4, 8]
    tmpdir = tempfile.mkdtemp(prefix="eval1_")
    rows = []
    print(f"Eval-1 | items={N_ITEMS} evs/item={EVS} total_events={N_ITEMS*EVS} | trials/cell={R} | jitter={JITTER}s")
    print(f"{'cond':<5}{'K':<4}{'lost_mean':>11}{'lost_max':>10}{'corrupt_mean':>14}{'correct_rate':>14}")
    CNAME = {"A": "A naive RMW", "B": "B naive append", "C": "C locked append"}
    for cond in ["A", "B", "C"]:
        for K in Ks:
            res = []
            for t in range(R):
                events, ground = make_workload(N_ITEMS, EVS, seed=1000*K + t)
                res.append(run_trial(cond, K, events, ground, JITTER, tmpdir, t))
            lost = [r["lost"] for r in res]
            corr = [r["corrupt"] for r in res]
            ok = [r["correct"] for r in res]
            tot = res[0]["total_events"]
            row = {"cond": cond, "K": K,
                   "lost_mean": round(statistics.mean(lost), 2),
                   "lost_max": max(lost),
                   "lost_pct_mean": round(100*statistics.mean(lost)/tot, 1),
                   "corrupt_mean": round(statistics.mean(corr), 2),
                   "correct_rate": round(100*statistics.mean(ok), 1),
                   "total_events": tot, "trials": R}
            rows.append(row)
            print(f"{CNAME[cond]:<16}K={K:<3}{row['lost_mean']:>8} ({row['lost_pct_mean']}%)  max={row['lost_max']:<5} corrupt={row['corrupt_mean']:<6} correct={row['correct_rate']}%")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval1_results.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("CSV ->", out)
    # optional figure
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        sub = lambda c: [r for r in rows if r["cond"]==c]
        plt.figure(figsize=(5.2,3.3))
        plt.plot([r["K"] for r in sub("A")], [r["lost_mean"] for r in sub("A")], "o-", color="#dc2626", label="A: naive shared-doc (RMW)")
        plt.plot([r["K"] for r in sub("B")], [r["lost_mean"] for r in sub("B")], "^--", color="#d97706", label="B: naive append (non-atomic)")
        plt.plot([r["K"] for r in sub("C")], [r["lost_mean"] for r in sub("C")], "s-", color="#2563eb", label="C: locked append + id-merge (ours)")
        plt.xlabel("concurrent sessions (K)"); plt.ylabel("lost updates (mean of 15 trials)")
        plt.title("Lost updates vs concurrency (80 events)"); plt.legend(); plt.grid(alpha=.3); plt.tight_layout()
        fig = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig5_lost_updates.png")
        plt.savefig(fig, dpi=140); print("FIG ->", fig)
    except Exception as e:
        print("matplotlib 미설치/오류 — CSV만 생성:", e)

if __name__ == "__main__":
    mp.freeze_support()
    main()
