from __future__ import annotations
import json, sqlite3
from pathlib import Path

DB = "r34.db"
BINS = 500  # разбиваем всю базу на 500 интервалов по ID

def main():
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT id, change_ts FROM posts WHERE change_ts > 1200000000 ORDER BY id"
    ).fetchall()
    
    if not rows:
        raise RuntimeError("В базе нет постов с change_ts")

    step = max(1, len(rows) // BINS)
    raw_pts = []
    for i in range(0, len(rows), step):
        chunk = rows[i:i + step]
        # Берем минимальный ID и самый старый change_ts в этом чанке (~900 постов)
        mid_id = chunk[len(chunk) // 2][0]
        min_ts = min(r[1] for r in chunk)
        raw_pts.append((mid_id, min_ts))

    # Делаем ряд строго неубывающим справа налево (если в будущем был пост из 2011,
    # то посты с меньшим ID точно не могли выйти позже него!)
    clean_pts = []
    min_so_far = float("inf")
    for pid, ts in reversed(raw_pts):
        if ts < min_so_far:
            min_so_far = ts
        clean_pts.append([pid, float(min_so_far)])
    clean_pts.reverse()

    # Явно фиксируем самую левую точку на первом ID из базы с его реальным минимальным ts
    first_id = rows[0][0]
    if clean_pts[0][0] > first_id:
        clean_pts.insert(0, [first_id, clean_pts[0][1]])

    Path("curve.json").write_text(json.dumps(clean_pts))
    print(f"Построено точек: {len(clean_pts)} по {len(rows)} постам -> curve.json")

if __name__ == "__main__":
    main()
