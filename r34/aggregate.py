from __future__ import annotations
import argparse, bisect, json, math, sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

NOISE = {"tagme", "1girl", "1girls", "1boy", "solo", "absurd_res", "hi_res",
         "highres", "high_quality", "high_resolution", "commentary",
         "english_commentary", "artist_name", "signature", "watermark",
         "absurdres", "ai_generated", "ai", "ai_art", "ai_assisted"}


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default="general,copyright,character,artist,metadata")
    ap.add_argument("--ratings", default="explicit,questionable,safe")
    ap.add_argument("--min-total", type=int, default=80)
    ap.add_argument("--min-years", type=int, default=5)
    ap.add_argument("--max-global", type=int, default=3_000_000)
    ap.add_argument("--max-jump", type=float, default=8.0)
    ap.add_argument("--sort", choices=["total", "trend"], default="total")
    ap.add_argument("--top", type=int, default=300)
    ap.add_argument("--out", default="web/data.json")
    a = ap.parse_args()
    keep = set(a.types.split(","))
    ratings = set(a.ratings.split(","))

    curve = Curve(json.loads(Path("curve.json").read_text()))
    con = sqlite3.connect("r34.db")

    per_year, counts, meta = Counter(), defaultdict(Counter), {}
    for pid, tags, ti, rating in con.execute(
            "SELECT id, tags, tag_info, rating FROM posts"):
        if rating not in ratings:
            continue
        y = curve.year(pid)
        per_year[y] += 1
        info = json.loads(ti or "{}")
        for t in tags.split():
            typ, g = info.get(t, ["general", 0])
            meta[t] = (typ, g)
            if typ in keep and g <= a.max_global:
                counts[y][t] += 1

    years = sorted(y for y in per_year if per_year[y] >= 100)

    def edge(sh, i, k=3):
        sel = [sh[y] for y in years[i:i + k]]
        return sum(sel) / len(sel) if sel else 0.0

    rows = []
    for t, (typ, g) in meta.items():
        if typ not in keep or g > a.max_global:
            continue
        sh = {y: counts[y][t] / per_year[y] for y in years}
        total = sum(counts[y][t] for y in years)
        present = len([y for y in years if counts[y][t]])
        if total < a.min_total or present < a.min_years:
            continue
        jumps = [sh[y2] / sh[y1] for y1, y2 in zip(years, years[1:]) if sh[y1] > 0]
        jump = max(jumps) if jumps else 1.0
        trend = (edge(sh, -3) + 1e-6) / (edge(sh, 0) + 1e-6)
        p = edge(sh, -3)
        n_last = sum(per_year[y] for y in years[-3:]) / max(1, len(years[-3:]))
        margin = 1.96 * math.sqrt(max(p * (1 - p), 0) / max(n_last, 1))
        rows.append({"tag": t, "type": typ, "total": total, "jump": round(jump, 1),
                     "trend": round(trend, 3), "margin": round(margin, 5),
                     "shares": {str(y): round(v, 6) for y, v in sh.items()}})

    if a.max_jump:
        rows = [r for r in rows if r["jump"] <= a.max_jump]
    rows.sort(key=(lambda r: -r["trend"]) if a.sort == "trend" else (lambda r: -r["total"]))
    Path(a.out).write_text(json.dumps(
        {"years": [str(y) for y in years], "n": dict(per_year),
         "ratings": sorted(ratings), "tags": rows[:a.top]}, ensure_ascii=False))
    print(f"{len(rows)} тегов, {len(years)} лет → web/data.json")


main()