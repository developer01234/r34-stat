from __future__ import annotations
import json, sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from itertools import permutations

import aggregate as agg  # нужен Curve

MIN_POSTS = 50
RATIO = (0.7, 1.4)
COOC = 0.5


def main():
    curve = agg.Curve(json.loads(Path("curve.json").read_text()))
    con = sqlite3.connect("r34.db")

    first, last, total = {}, {}, Counter()
    for pid, tags in con.execute("SELECT id, tags FROM posts"):
        y = curve.year(pid)
        for t in tags.split():
            total[t] += 1
            if t not in first or y < first[t]:
                first[t] = y
            if t not in last or y > last[t]:
                last[t] = y

    cand = []

    by_first = defaultdict(list)
    for t, n in total.items():
        if n >= MIN_POSTS:
            by_first[first[t]].append(t)
    for a, na in total.items():
        if na < MIN_POSTS:
            continue
    for y in (last[a] - 1, last[a], last[a] + 1):
        for b in by_first.get(y, []):
            if b != a and RATIO[0] <= na / total[b] <= RATIO[1]:
                cand.append((a, b))

    print(f"кандидатов: {len(cand)}")

    pairs = {frozenset(p) for p in cand}

    cand_set = set(cand)
    valid_tags = {t for pair in cand for t in pair}

    both = Counter()
    for (tags,) in con.execute("SELECT tags FROM posts"):
        s = [t for t in set(tags.split()) if t in valid_tags]
        for a, b in permutations(s, 2):
            if (a, b) in cand_set:
                both[(a, b)] += 1
    found = []
    for a, b in cand:
        share = both[(a, b)] / total[a]
        if share >= COOC:
            found.append({"old": a, "new": b, "posts_old": total[a],
                          "posts_new": total[b], "cooc": round(share, 2),
                          "last_year": last[a], "first_year": first[b]})
    found.sort(key=lambda x: -x["cooc"])
    Path("aliases.json").write_text(json.dumps(found, ensure_ascii=False, indent=1))
    for f in found[:40]:
        print(f'{f["old"]} -> {f["new"]}  cooc={f["cooc"]}  {f["last_year"]}->{f["first_year"]}')


main()