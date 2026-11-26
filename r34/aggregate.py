from __future__ import annotations
import argparse, bisect, json, math, sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

NOISE = {"tagme", "1girl", "1girls", "1boy", "solo", "absurd_res",
         "high_quality", "commentary", "english_commentary", "artist_name",
         "signature", "watermark"}

ALL_TYPES = "general,copyright,character,artist,metadata"


class Curve:
    def __init__(self, pts):
        self.x = [p[0] for p in pts]
        self.y = [p[1] for p in pts]

    def year(self, post_id):
        i = bisect.bisect_left(self.x, post_id)
        if i == 0:
            ts = self.y[0]
        elif i >= len(self.x):
            ts = self.y[-1]
        else:
            x0, x1, y0, y1 = self.x[i-1], self.x[i], self.y[i-1], self.y[i]
            ts = y0 + (y1 - y0) * (post_id - x0) / max(1, x1 - x0)
        return datetime.fromtimestamp(ts, timezone.utc).year

def load_aliases(path):
    return {p["old"]: p["new"] for p in
            json.loads(Path(path).read_text(encoding="utf-8"))
            if p["old"] != p["new"]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default=ALL_TYPES)
    ap.add_argument("--ratings", default="explicit,questionable,safe")
    ap.add_argument("--min-total", type=int, default=80)
    ap.add_argument("--min-total-rare", type=int, default=5)
    ap.add_argument("--min-years", type=int, default=5)
    ap.add_argument("--min-years-rare", type=int, default=2)
    ap.add_argument("--max-global", type=int, default=3_000_000)
    ap.add_argument("--max-jump", type=float, default=8.0)
    ap.add_argument("--sort", choices=["total", "trend", "ai"], default="total")
    ap.add_argument("--top", type=int, default=300)
    ap.add_argument("--flat", action="store_true")
    ap.add_argument("--aliases", nargs="+", default=[])
    ap.add_argument("--out", default="data.json")
    ap.add_argument("--allow", default="")
    a = ap.parse_args()

    keep = set(x for x in a.types.split(",") if x)
    ratings = set(a.ratings.split(","))
    allow = set(x for x in a.allow.split(",") if x)
    print(f"types={sorted(keep)}")

    raw = {}
    for path in a.aliases:
        if Path(path).exists():
            raw.update(load_aliases(path))

    def final(t):
        seen = set()
        while t in raw and t not in seen:
            seen.add(t)
            t = raw[t]
        return t

    amap = {k: final(k) for k in raw}
    if amap:
        print(f"алиасов: {len(amap)}")

    curve = Curve(json.loads(Path("curve.json").read_text()))
    con = sqlite3.connect("r34.db")

    per_year, counts, meta = Counter(), defaultdict(Counter), {}
    ai_by_year = Counter()
    ai_counts = defaultdict(Counter)

    for pid, tags, ti, rating in con.execute(
            "SELECT id, tags, tag_info, rating FROM posts"):
        if rating not in ratings:
            continue
        y = curve.year(pid)
        per_year[y] += 1
        is_ai = "ai_generated" in tags
        if is_ai:
            ai_by_year[y] += 1
        info = json.loads(ti or "{}")
        seen = set()
        for tok in tags.split():
            typ, g = info.get(tok, ["general", 0])
            r = amap.get(tok, tok)
            if r in seen:
                continue
            seen.add(r)
            meta[r] = (typ, g)
            if typ in keep and (g <= a.max_global or r in allow):
                counts[y][r] += 1
                if is_ai:
                    ai_counts[y][r] += 1

    years = sorted(y for y in per_year if per_year[y] >= 100)

    def mean(vals):
        return sum(vals) / len(vals) if vals else 0.0

    rows = []
    for t, (typ, g) in meta.items():
        if typ not in keep or (g > a.max_global and t not in allow):
            continue
        rare = typ in ("artist", "character")
        floor = a.min_total_rare if rare else a.min_total
        need_years = a.min_years_rare if rare else a.min_years
        sh = {y: counts[y][t] / per_year[y] for y in years}
        total = sum(counts[y][t] for y in years)
        present = len([y for y in years if counts[y][t]])
        if total < floor or present < need_years:
            continue
        jumps = [sh[y2] / sh[y1] for y1, y2 in zip(years, years[1:]) if sh[y1] > 0]
        jump = max(jumps) if jumps else 1.0
        nz = [i for i, y in enumerate(years) if counts[y][t]]
        i0, i1 = nz[0], nz[-1]
        bi = i0
        while bi < i1 and mean([sh[years[i]] for i in range(bi, min(bi + 3, len(years)))]) < 0.001:
            bi += 1
        w_first = range(bi, min(bi + 3, len(years)))
        w_first = range(bi, min(bi + 3, len(years)))
        w_last = range(max(i1 - 2, 0), i1 + 1)
        p_first = mean([sh[years[i]] for i in w_first])
        p_last = mean([sh[years[i]] for i in w_last])
        n_last = mean([per_year[years[i]] for i in w_last]) or 1

        trend = (p_last + 1e-6) / (p_first + 1e-6)
        margin = 1.96 * math.sqrt(max(p_last * (1 - p_last), 0) / n_last)

        ai_share = sum(ai_counts[y][t] for y in years) / total if total else 0.0
        rows.append({"tag": t, "type": typ, "total": total, "jump": round(jump, 1),
                     "trend": round(min(trend, 9999.0), 2),
                     "margin": round(margin, 5),
                     "ai": round(ai_share, 4),
                     "shares": {str(y): round(v, 6) for y, v in sh.items()}})

    if a.max_jump:
        rows = [r for r in rows if r["jump"] <= a.max_jump or r["tag"] in allow]

    keys = {"trend": lambda r: -r["trend"], "ai": lambda r: -r["ai"],
            "total": lambda r: -r["total"]}
    if a.flat:
        rows.sort(key=keys[a.sort])
        rows = rows[:a.top]
    else:
        picked = []
        for typ in sorted(keep):
            sub = [r for r in rows if r["type"] == typ]
            sub.sort(key=keys[a.sort])
            print(f"  {typ}: {len(sub)} после фильтров")
            picked += sub[:a.top]
        rows = sorted(picked, key=lambda r: -r["total"])

    Path(a.out).write_text(json.dumps(
        {"years": [str(y) for y in years], "n": dict(per_year),
         "ai": {str(y): round(ai_by_year[y] / per_year[y], 4) for y in years},
         "ratings": sorted(ratings), "tags": rows}, ensure_ascii=False))
    print(f"{len(rows)} тегов → {a.out}")


if __name__ == "__main__":
    main()