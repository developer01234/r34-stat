from __future__ import annotations
import asyncio, json, sqlite3, statistics
from pathlib import Path
import httpx
from r34.harvest import fetch, UA, DB, max_id

POINTS, WIDTH = 400, 250


def pava(xs, ys):
    """Pool-adjacent-violators: РґРµР»Р°РµРј СЂСЏРґ РјРѕРЅРѕС‚РѕРЅРЅРѕ РЅРµСѓР±С‹РІР°СЋС‰РёРј."""
    blocks = [[x, y, 1] for x, y in zip(xs, ys)]
    out = []
    for b in blocks:
        out.append(b)
        while len(out) > 1 and out[-2][1] / out[-2][2] > out[-1][1] / out[-1][2]:
            y2, n2 = out.pop()[1:]
            out[-1][1] += y2
            out[-1][2] += n2
    return [(b[0], b[1] / b[2]) for b in out]


async def main():
    con = sqlite3.connect(DB)
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=90) as client:
        top = await max_id(client)
    step = max(1, top // POINTS)
    pts = []
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=60) as client:
        for lo in range(1, top - WIDTH, step):
            posts = await fetch(client, f"id:>{lo} id:<{lo + WIDTH}", limit=1000)
            # change >= upload; РјРёРЅРёРјСѓРј РїРѕ РѕРєРЅСѓ вЂ” Р»СѓС‡С€Р°СЏ РѕС†РµРЅРєР° РІСЂРµРјРµРЅРё Р·Р°РіСЂСѓР·РєРё
            ts = [int(p["change"]) for p in posts if p.get("change")]
            if len(ts) >= 5:
                pts.append((lo + WIDTH // 2, min(ts)))
            print(f"{lo}: {len(ts)}", end="\r", flush=True)
    pts.sort()
    curve = pava([p[0] for p in pts], [p[1] for p in pts])
    Path("curve.json").write_text(json.dumps(curve))
    print(f"\nС‚РѕС‡РµРє: {len(curve)} в†’ curve.json")


asyncio.run(main())