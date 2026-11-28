import asyncio, datetime, httpx
from r34.harvest import fetch, UA


async def main():
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=60) as c:
        for lo in (500, 2000, 10000, 50000, 150000, 400000):
            p = await fetch(c, f"id:>{lo} id:<{lo + 200}")
            ds = sorted({datetime.datetime.fromtimestamp(
                int(x["change"]), datetime.timezone.utc).strftime("%Y-%m")
                for x in p if x.get("change")})
            print(lo, len(p), ds[:6])


asyncio.run(main())