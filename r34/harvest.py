from __future__ import annotations
import argparse, asyncio, gzip, json, os, random, sqlite3, time
from pathlib import Path
import httpx

API = "https://api.rule34.xxx/index.php"
DB = Path(os.environ.get("R34_DB", "r34.db"))
RAW = Path(os.environ.get("R34_RAW", "raw"))
UA = "r34-tagtrends/0.1 (personal research)"


def load_env(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


load_env()

USER_ID = os.environ["R34_USER_ID"]
API_KEY = os.environ["R34_API_KEY"]
RPS = float(os.environ.get("R34_RPS", "1.0"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts(
  id INTEGER PRIMARY KEY, change_ts INTEGER, score INTEGER,
  rating TEXT, tags TEXT, tag_info TEXT
);
CREATE TABLE IF NOT EXISTS windows(
  lo INTEGER, hi INTEGER, done INTEGER DEFAULT 0, PRIMARY KEY(lo,hi)
);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS posts_change ON posts(change_ts);
"""

TYPE_MAP = {"tag": "general"}
_lock, _last = asyncio.Lock(), 0.0


async def throttle():
    global _last
    async with _lock:
        wait = _last + 1 / RPS - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        _last = time.monotonic()


def normalize(data):
    if data in ("", None):
        return []
    if isinstance(data, dict):
        if data.get("success") is False:
            raise RuntimeError(data.get("message", "api error"))
        return [data] if "id" in data else []
    return data


def tag_info(post):
    """tag_info: [{count,type,tag}] -> {tag: [type, global_count]}"""
    out = {}
    for d in post.get("tag_info") or []:
        if isinstance(d, dict) and d.get("tag"):
            t = d.get("type") or "general"
            out[d["tag"]] = [TYPE_MAP.get(t, t), int(d.get("count") or 0)]
    return out


async def fetch(client, tags, limit=1000, retries=6):
    params = {"page": "dapi", "s": "post", "q": "index", "json": 1,
              "limit": limit, "tags": tags, "fields": "tag_info",
              "user_id": USER_ID, "api_key": API_KEY}
    for attempt in range(retries):
        await throttle()
        try:
            r = await client.get(API, params=params)
            if r.status_code in (429, 502, 503, 504):
                raise httpx.HTTPStatusError("busy", request=r.request, response=r)
            r.raise_for_status()
            body = r.text.strip()
            if not body:
                raise RuntimeError("empty body")
            if "API limited" in body:
                raise RuntimeError("API limited due to abuse")
            return normalize(json.loads(body))
        except (httpx.HTTPError, json.JSONDecodeError, RuntimeError) as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(min(60, 2 ** (attempt + 1)))

def save(con, posts, lo, hi):
    con.executemany(
        "INSERT OR REPLACE INTO posts VALUES(?,?,?,?,?,?)",
        [(p["id"], int(p.get("change") or 0), int(p.get("score") or 0),
          p.get("rating"), p.get("tags") or "", json.dumps(tag_info(p)))
         for p in posts])
    con.execute("INSERT OR REPLACE INTO windows VALUES(?,?,1)", (lo, hi))
    con.commit()


async def max_id(client):
    posts = await fetch(client, "id:>0", limit=1)
    return posts[0]["id"] if posts else 0


async def crawl(client, con, top):
    row = con.execute("SELECT v FROM meta WHERE k='cursor'").fetchone()
    hi = int(row[0]) if row else top + 1
    while hi > 1:
        posts = await fetch(client, f"id:<{hi}")
        if not posts:
            break
        lo = min(p["id"] for p in posts)
        save(con, posts, lo, hi)
        con.execute("INSERT OR REPLACE INTO meta VALUES('cursor',?)", (str(lo),))
        con.commit()
        print(f"cursor {lo} ({len(posts)})", flush=True)
        hi = lo

async def sample(client, con, n, width, seed=34):
    top = await max_id(client)
    rng = random.Random(seed)
    windows = [(lo, lo + width) for lo in sorted(rng.sample(range(1, top - width), n))]
    done = {r[0] for r in con.execute("SELECT lo FROM windows WHERE done=1")}
    print(f"max id {top}; окон: {len(windows)} (пропуск {len(done)})", flush=True)
    RAW.mkdir(exist_ok=True)

    async def grab(lo, hi):
        posts = await fetch(client, f"id:>{lo} id:<{hi}")
        if posts:
            save(con, posts, lo, hi)
            with gzip.open(RAW / f"{lo}.json.gz", "wt") as f:
                json.dump(posts, f)
        return len(posts)

    fails = []
    for i, (lo, hi) in enumerate(windows, 1):
        if lo in done:
            continue
        try:
            print(f"[{i}/{len(windows)}] {lo} -> {await grab(lo, hi)}", flush=True)
        except Exception as e:
            print(f"[{i}/{len(windows)}] {lo} FAIL {type(e).__name__}: {e}", flush=True)
            fails.append((lo, hi))

    if fails:
        print(f"паузa 120 с, затем {len(fails)} повторов", flush=True)
        await asyncio.sleep(120)
        for lo, hi in fails:
            try:
                print(f"retry {lo} -> {await grab(lo, hi)}", flush=True)
            except Exception as e:
                print(f"retry {lo} снова FAIL {type(e).__name__}: {e}", flush=True)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["sample", "full"], default="sample")
    ap.add_argument("--samples", type=int, default=1500)
    ap.add_argument("--width", type=int, default=100)
    ap.add_argument("--seed", type=int, default=34)
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    if a.reset:
        con.executescript("DELETE FROM posts; DELETE FROM windows; DELETE FROM meta;")
        con.commit()

    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=90) as client:
        if a.mode == "full":
            await crawl(client, con, await max_id(client))
        else:
            await sample(client, con, a.samples, a.width, a.seed)


if __name__ == "__main__":
    asyncio.run(main())