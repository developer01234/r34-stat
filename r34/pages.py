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

def badge(t, years):
    vals = [t["shares"].get(y, 0) for y in years]
    mx = max(vals) or 1
    n = len(vals) - 1 or 1
    pts = " ".join(f"{112 + i * (74 / n):.1f},{23 - (v / mx) * 18:.1f}"
                   for i, v in enumerate(vals))
    label = html.escape(t["tag"])[:16]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="28">'
            f'<rect width="200" height="28" rx="4" fill="#1b1b1b"/>'
            f'<text x="6" y="18" font-family="system-ui" font-size="11" '
            f'fill="#ddd">{label}</text>'
            f'<polyline points="{pts}" fill="none" stroke="#6aa8e8" stroke-width="1.5"/>'
            f'</svg>')

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
    desc = (f"{t['tag']} on rule34.xxx: share of posts by year, peak {peak:.2f}% "
            f"in {peak_y}, now {cur:.2f}%.")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t['tag'])} — popularity by year | r34 tag trends</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{base}/tag/{slug(t['tag'])}.html">
<script src="../i18n.js"></script>
<style>
 body{{background:#111;color:#ddd;font:14px system-ui;margin:0;padding:24px;max-width:760px}}
 a{{color:#6aa8e8}} h1{{font-size:22px;margin:0 0 4px}}
 .type{{font-size:12px;color:{color}}}
 table{{border-collapse:collapse;margin:18px 0}}
 td,th{{padding:2px 10px;text-align:left;font-weight:400;border-bottom:1px solid #222}}
 .k{{color:#888}} footer{{color:#777;font-size:12px;margin-top:28px;line-height:1.6}}
 button{{background:#1b1b1b;color:#ddd;border:1px solid #444;padding:2px 6px}}
</style></head><body>
<p><a href="../" data-i18n="dash">← dashboard</a>
 <a href="./" data-i18n="back">← all tags</a>
 <button onclick="setLang(localStorage.lang==='en'?'ru':'en')">EN / RU</button></p>
<h1>{html.escape(t['tag'])}</h1>
<p class="type"><span data-i18n="type">type</span>: {t['type']}</p>
{spark(vals, years, color)}
<p><span class="k" data-i18n="peak">peak</span>: {peak:.2f}% {peak_y} &nbsp;
<span class="k" data-i18n="now">now</span>: {cur:.2f}% &nbsp;
<span class="k" data-i18n="trend">trend</span>: {t['trend']}× &nbsp;
<span class="k" data-i18n="aish">AI</span>: {(t['ai'] * 100):.1f}%
<svg width="120" height="7" style="vertical-align:middle">
<rect width="120" height="7" fill="#222"/>
<rect width="{t['ai'] * 120:.0f}" height="7" fill="#888"/>
</svg> &nbsp;
<span class="k" data-i18n="pm">±</span>: {(t['margin'] * 100):.1f}</p>
<table><tr><th data-i18n="year">year</th><th>%</th><th>n</th></tr>{rows}</table>
<p><span class="k" data-i18n="related">related</span>: {links}</p>
<p><span class="k" data-i18n="badge">badge</span>:
<code>&lt;img src="{base}/badge/{slug(t['tag'])}.svg"&gt;</code></p>
<p class="k" data-i18n="ainote">AI share</p>
<footer data-i18n="foot"> </footer>
</body></html>"""

def method(d, years, base):
    total = sum(d["n"].values())
    rows = "".join(f"<tr><td>{y}</td><td>{d['n'].get(y, 0)}</td></tr>" for y in years)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>methodology | r34 tag trends</title>
<meta name="description" content="How tag trends are computed: ID-to-date calibration, sampling, confidence intervals, and known artifacts.">
<link rel="canonical" href="{base}/method.html">
<meta name="robots" content="index,follow">
<style>
 body{{background:#111;color:#ddd;font:14px system-ui;padding:24px;max-width:760px;line-height:1.65}}
 a{{color:#6aa8e8}} h2{{font-size:16px;margin-top:26px}} code{{color:#e0b23a}}
 table{{border-collapse:collapse}} td,th{{padding:2px 12px;border-bottom:1px solid #222;text-align:left}}
</style></head>
<p><a href="./">← дашборд</a></p>
<h1>Методика</h1>
<p>Проект считает, какую долю постов в каждом году составляли посты с данным тегом.
Выборка: <b>{total}</b> постов за {years[0]}–{years[-1]}.</p>

<h2>Откуда берётся год</h2>
<p>API rule34.xxx не отдаёт дату загрузки. Единственная метка времени в ответе —
<code>change</code>, время последней правки поста, и оно всегда не меньше времени загрузки.
Посты сортируются по ID, а ID растут монотонно, поэтому год восстанавливается по ID:
окна ID сопоставляются с минимальным <code>change</code> в окне, ряд сглаживается
монотонно (pool-adjacent-violators), затем пост относится к году по интерполяции.</p>
<p>Это <b>оценка</b>. Ретэггинг старых постов сдвигает её вперёд, и на границах годов
возможна ошибка в несколько месяцев.</p>

<h2>Выборка</h2>
<p>Окна ID отбираются случайно по всему диапазону, а не по порядку, чтобы не смещаться
к свежим загрузкам. Размер выборки по годам:</p>
<table><tr><th>год</th><th>постов</th></tr>{rows}</table>
<p>Ранние годы представлены слабо: до 2014 загрузок было меньше, и случайный семпл
попадает туда редко. Левый край графиков шумный, доли там — прикидка.</p>

<h2>Погрешность</h2>
<p>Колонка «±» — 95% доверительный интервал, посчитанный как
<code>1.96·√(p(1−p)/n)</code> на последних трёх годах. При доле 10% и n=3000 это ±1.1 п.п.
Разница меньше интервала — не сигнал.</p>

<h2>Артефакты</h2>
<p>Колонка «скачок» — максимальный рост доли за один год. Значения выше 8 отбрасываются:
такой профиль означает введение тега или волну ретэггинга, а не смену вкусов.
Пример — <code>genitals</code>: 0.4% в 2020 и 22% в 2021, рост в 54 раза.</p>
<p>Плавная смена конвенции разметки фильтром не ловится. Падение <code>human</code>
в основном означает, что вид перестали указывать, а не что людей на картинках стало меньше.</p>

<h2>Что не измеряется</h2>
<p>Доля — не качество и не просмотры. <code>score</code> для этого не годится: голосуют редко,
значения 0 и 1. Удалённые посты в выборку не попадают, то есть история слегка
отцензурена модерацией.</p>

<h2>Данные и лицензия</h2>
<p>Сырые агрегаты: <a href="data.json">data.json</a>. Код: MIT.
Данные принадлежат rule34.xxx и авторам загрузок. Проект неофициальный.</p>
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

    # --- сюда первый блок: список тегов ---
    idx = "".join(f'<li><a href="{slug(t["tag"])}.html">{html.escape(t["tag"])}</a> '
                  f'<span class="k">{t["type"]}</span></li>' for t in tags)

    # --- и сразу за ним второй: сама страница индекса ---
    (out / "index.html").write_text(
        f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>all tags</title>
<script src="../i18n.js"></script>
<style>body{{background:#111;color:#ddd;font:14px system-ui;padding:24px}}
a{{color:#6aa8e8}} .k{{color:#777;font-size:11px}} li{{margin:3px 0}}</style>
<p><a href="../" data-i18n="dash">← dashboard</a>
<button onclick="setLang(localStorage.lang==='en'?'ru':'en')">EN / RU</button></p>
<h1 data-i18n="tags">all tags</h1><ul>{idx}</ul>""", encoding="utf-8")

    (Path("web") / "method.html").write_text(method(d, years, a.base), encoding="utf-8")

    bad = Path("web/badge")
    bad.mkdir(parents=True, exist_ok=True)
    for t in tags:
        (bad / f"{slug(t['tag'])}.svg").write_text(badge(t, years), encoding="utf-8")

    urls = [f"{a.base}/", f"{a.base}/method.html", f"{a.base}/compare.html"]
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