from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="r34.db")
    ap.add_argument("--bins", type=int, default=500)
    ap.add_argument("--id-min", type=int, default=120000)
    ap.add_argument("--min-ts", type=int, default=1200000000)
    a = ap.parse_args()

    con = sqlite3.connect(a.db)
    rows = con.execute(
        "SELECT id, change_ts FROM posts WHERE id >= ? AND change_ts > ? ORDER BY id",
        (a.id_min, a.min_ts),
    ).fetchall()
    if len(rows) < a.bins * 2:
        raise RuntimeError(f"мало постов после фильтра: {len(rows)}")

    step = max(1, len(rows) // a.bins)
    raw = []
    for i in range(0, len(rows) - step + 1, step):
        chunk = rows[i:i + step]
        raw.append((chunk[len(chunk) // 2][0], min(r[1] for r in chunk)))

    clean = []
    low = float("inf")
    for pid, ts in reversed(raw):
        low = min(low, ts)
        clean.append([pid, float(low)])
    clean.reverse()

    clean.insert(0, [float(a.id_min), clean[0][1]])
    assert all(x[1] <= y[1] for x, y in zip(clean, clean[1:]))

    Path("curve.json").write_text(json.dumps(clean))
    print(f"{len(clean)} точек по {len(rows)} постам, "
          f"ID {clean[0][0]:.0f}..{clean[-1][0]:.0f} → curve.json")


if __name__ == "__main__":
    main()