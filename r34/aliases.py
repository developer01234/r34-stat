from __future__ import annotations
import argparse, difflib, json, math, re, sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from aggregate import Curve


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fuzzy", "time"], default="fuzzy")
    ap.add_argument("--sim", type=float, default=0.93)
    ap.add_argument("--min-total", type=int, default=40)
    ap.add_argument("--dead-months", type=int, default=2)
    ap.add_argument("--ratio", type=float, nargs=2, default=(0.7, 1.4))
    ap.add_argument("--vol", type=float, nargs=2, default=(0.4, 2.5))
    ap.add_argument("--out", default="aliases.json")
    a = ap.parse_args()

    curve = Curve(json.loads(Path("curve.json").read_text()))
    con = sqlite3.connect("r34.db")

    def mkey(pid):
        i = __import__("bisect").bisect_left(curve.x, pid)
        if i == 0:
            ts = curve.y[0]
        elif i >= len(curve.x):
            ts = curve.y[-1]
        else:
            x0, x1, y0, y1 = curve.x[i-1], curve.x[i], curve.y[i-1], curve.y[i]
            ts = y0 + (y1 - y0) * (pid - x0) / max(1, x1 - x0)
        d = datetime.fromtimestamp(ts, timezone.utc)
        return d.year * 12 + d.month - 1

    first, last, total, types = {}, {}, Counter(), {}
    months = defaultdict(Counter)
    max_m = 0
    for pid, tags, ti in con.execute("SELECT id, tags, tag_info FROM posts"):
        m = mkey(pid)
        max_m = max(max_m, m)
        info = json.loads(ti or "{}")
        for t in tags.split():
            total[t] += 1
            months[t][m] += 1
            types[t] = info.get(t, ["general", 0])[0]
            if t not in first or m < first[t]:
                first[t] = m
            if t not in last or m > last[t]:
                last[t] = m

    found = []

    if a.mode == "fuzzy":
        norm = {t: re.sub(r"[^a-z0-9]", "", t.lower()) for t in total}
        GENDER = {"male": "male", "man": "male", "boy": "male",
                  "female": "female", "woman": "female", "girl": "female",
                  "futa": "futa", "futanari": "futa", "dickgirl": "futa"}

        def gset(t):
            return {GENDER[w] for w in re.split(r"[^a-z0-9]+", t.lower()) if w in GENDER}

        buckets = defaultdict(list)
        for t, n in norm.items():
            if total[t] >= a.min_total and len(n) >= 4:
                buckets[n[:4]].append(t)
        for group in buckets.values():
            for i, x in enumerate(group):
                for y in group[i + 1:]:
                    if types.get(x) != types.get(y):
                        continue
                    exact = norm[x] == norm[y]
                    if not exact:
                        if gset(x) != gset(y):
                            continue
                        if len(norm[x]) < 8:
                            continue
                    r = 1.0 if exact else difflib.SequenceMatcher(None, norm[x], norm[y]).ratio()
                    if r < a.sim:
                        continue
                    old, new = (x, y) if total[x] <= total[y] else (y, x)
                    found.append({"old": old, "new": new, "sim": round(r, 3),
                                  "exact": exact,
                                  "posts_old": total[old], "posts_new": total[new],
                                  "last_year": last[old] // 12,
                                  "first_year": first[new] // 12})
    else:
        peak = {t: max(c.values()) for t, c in months.items()}
        by_last = defaultdict(list)
        for t, n in total.items():
            if n >= a.min_total:
                by_last[last[t]].append(t)
        for new, n in total.items():
            if n < a.min_total:
                continue
            for old in by_last.get(first.get(new), []):
                if old == new or types.get(old) != types.get(new):
                    continue
                if not (a.ratio[0] <= n / total[old] <= a.ratio[1]):
                    continue
                if last[old] > max_m - a.dead_months or peak[old] < 10:
                    continue
                fm = first[new]
                tail = sum(c for mm, c in months[old].items() if fm - 2 <= mm <= fm)
                head = sum(c for mm, c in months[new].items() if fm <= mm <= fm + 2)
                if not head or tail / peak[old] > 0.3:
                    continue
                vr = tail / head
                if not (a.vol[0] <= vr <= a.vol[1]):
                    continue
                found.append({"old": old, "new": new, "vol": round(vr, 2),
                              "posts_old": total[old], "posts_new": total[new],
                              "last_year": last[old] // 12,
                              "first_year": fm // 12})

    raw = {f["old"]: f["new"] for f in found}

    def final(t):
        seen = set()
        while t in raw and t not in seen:
            seen.add(t)
            t = raw[t]
        return t

    best = {}
    for f in found:
        f["final"] = final(f["old"])
        if f["final"] == f["old"]:
            continue
        k = f["old"]
        if k not in best or (f.get("exact", False), f.get("sim", 0)) > \
                (best[k].get("exact", False), best[k].get("sim", 0)):
            best[k] = f

    out = sorted(best.values(), key=lambda f: -f.get("sim", 0))
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for f in out[:60]:
        mark = "=" if f.get("exact") else "~"
        print(f'{mark} {f["old"]} -> {f["final"]}  {f.get("sim", "")}  '
              f'{f["posts_old"]}/{f["posts_new"]}')


if __name__ == "__main__":
    main()
