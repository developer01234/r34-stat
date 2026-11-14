from __future__ import annotations
import argparse, html, json, math, re
from datetime import date
from pathlib import Path

TINT = {"metadata": "#e0b23a", "copyright": "#e87bb0", "character": "#5fbf6a",
        "artist": "#a8763e", "general": "#6aa8e8"}


def slug(tag):
    s = re.sub(r"[^a-z0-9]+", "_", tag.lower()).strip("_")
    return s or "tag"


def corr(a, b):
    n = len(a)
    if n < 3:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va == 0 or vb == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def spark(vals, years, color):
    mx = max(vals) or 1
    w, h, pad = 700, 150, 14
    step = (w - 2 * pad) / max(1, len(vals) - 1)
    pts = " ".join(f"{pad + i * step:.1f},{h - pad - (v / mx) * (h - 2 * pad):.1f}"
                   for i, v in enumerate(vals))
    peak_i = vals.index(max(vals))
    marks = "".join(
        f'<text x="{pad + i * step:.0f}" y="{h - 2}" fill="#666" font-size="10" '
        f'text-anchor="middle">{years[i]}</text>'
        for i in (0, len(years) // 2, len(years) - 1))
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:700px">'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>'
            f'<circle cx="{pad + peak_i * step:.1f}" '
            f'cy="{h - pad - (vals[peak_i] / mx) * (h - 2 * pad):.1f}" r="3" fill="#fff"/>'
            f'{marks}</svg>')


def page(t, d, years, rel, base):
    vals = [t["shares"].get(y, 0) * 100 for y in years]
    peak = max(vals)
    peak_y = years[vals.index(peak)]
    cur = vals[-1]
    color = TINT.get(t["type"], TINT["general"])
    rows = "".join(f"<tr><td>{y}</td><td>{v:.2f}%</td>"
                   f"<td>{d['n'].get(y, 0)}</td></tr>"
                   for y, v in zip(years, vals))
    links = " ".join(f'<a href="{slug(r)}.html">{html.escape(r)}</a>' for r in rel)
    desc = (f"{t['tag']} на rule34.xxx: доля постов по годам, пик {peak:.2f}% "
            f"в {peak_y}, сейчас {cur:.2f}%.")
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t['tag'])} — популярность по годам | r34 tag trends</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{base}/tag/{slug(t['tag'])}.html">
<style>
 body{{background:#111;color:#ddd;font:14px system-ui;margin:0;padding:24px;max-width:760px}}
 a{{color:#6aa8e8}} h1{{font-size:22px;margin:0 0 4px}}
 .type{{font-size:12px;color:{color}}}
 table{{border-collapse:collapse;margin:18px 0}}
 td,th{{padding:2px 10px;text-align:left;font-weight:400;border-bottom:1px solid #222}}
 .k{{color:#888}} footer{{color:#777;font-size:12px;margin-top:28px;line-height:1.6}}
</style></head>
<p><a href="../">← все теги</a></p>
<h1>{html.escape(t['tag'])}</h1>
<p class="type">тип: {t['type']}</p>
{spark(vals, years, color)}
<p><span class="k">пик:</span> {peak:.2f}% в {peak_y} &nbsp;
<span class="k">сейчас:</span> {cur:.2f}% &nbsp;
<span class="k">тренд:</span> {t['trend']}× &nbsp;
<span class="k">±:</span> {(t['margin'] * 100):.1f} п.п.</p>
<table><tr><th>год</th><th>доля</th><th>n</th></tr>{rows}</table>
<p><span class="k">похожие:</span> {links}</p>
<footer>Доля постов с тегом от всех постов года. Год восстановлен по ID поста,
это оценка, а не дата загрузки. n — размер выборки по году.
Данные: rule34.xxx. <a href="../">все теги</a>.</footer>
</html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://developer01234.github.io/r34-stat/web")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--related", type=int, default=6)
    ap.add_argument("--data", default="web/data.json")
    ap.add_argument("--out", default="web/tag")
    a = ap.parse_args()

    d = json.loads(Path(a.data).read_text(encoding="utf-8"))
    years = d["years"]
    tags = d["tags"][:a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    used, vecs = {}, {}
    for t in tags:
        s = slug(t["tag"])
        while s in used and used[s] != t["tag"]:
            s += "_"
        used[s] = t["tag"]
        vecs[t["tag"]] = [t["shares"].get(y, 0) for y in years]

    for t in tags:
        rel = [o["tag"] for o in tags if o["tag"] != t["tag"]]
        rel.sort(key=lambda o: -corr(vecs[t["tag"]], vecs[o]))
        (out / f"{slug(t['tag'])}.html").write_text(
            page(t, d, years, rel[:a.related], a.base), encoding="utf-8")

    idx = "".join(f'<li><a href="{slug(t["tag"])}.html">{html.escape(t["tag"])}</a> '
                  f'<span class="k">{t["type"]}</span></li>' for t in tags)
    (out / "index.html").write_text(
        f"""<!doctype html><meta charset="utf-8"><title>все теги | r34 tag trends</title>
<style>body{{background:#111;color:#ddd;font:14px system-ui;padding:24px}}
a{{color:#6aa8e8}} .k{{color:#777;font-size:11px}} li{{margin:3px 0}}</style>
<p><a href="../">← дашборд</a></p><h1>Теги</h1><ul>{idx}</ul>""", encoding="utf-8")

    urls = [f"{a.base}/"]
    for f in sorted(Path("web").glob("*/")):
        urls += [f"{a.base}/{f.name}/{p.name}" for p in sorted(f.glob("*.html"))]
    today = date.today().isoformat()
    (Path("web") / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (Path("web") / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {a.base}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(tags)} страниц + sitemap")


main()