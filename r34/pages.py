from __future__ import annotations
import argparse, json, math, re
from collections import defaultdict
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
    label = html_escape(t["tag"])[:16]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="28">'
            f'<rect width="200" height="28" rx="4" fill="#1b1b1b"/>'
            f'<text x="6" y="18" font-family="system-ui" font-size="11" '
            f'fill="#ddd">{label}</text>'
            f'<polyline points="{pts}" fill="none" stroke="#6aa8e8" stroke-width="1.5"/>'
            f'</svg>')


def html_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def page(t, d, years, rel, base, slugs):
    vals = [t["shares"].get(y, 0) * 100 for y in years]
    peak = max(vals)
    peak_y = years[vals.index(peak)]
    cur = vals[-1]
    dyears = [f"≤{years[0]}"] + [str(y) for y in years[1:]]
    color = TINT.get(t["type"], TINT["general"])
    tr = f"{t['trend']:.0f}" if t["trend"] >= 10 else f"{t['trend']:.1f}" # <-- Вставьте сюда
    rows = "".join(f"<tr><td>{y}</td><td>{v:.2f}%</td>"
                   f"<td>{d['n'].get(y, 0)}</td></tr>"
                   for y, v in zip(dyears, vals))
    labels = {"artist": "artists", "copyright": "franchises", "character": "characters",
              "general": "similar", "metadata": "related meta"}
    blocks = ""
    for typ, lst in rel.items():
        if not lst:
            continue
        blocks += (f'<p><span class="k">{labels.get(typ, typ)}</span>: '
                   + " ".join(f'<a href="{slugs.get(r, slug(r))}.html">{html_escape(r)}</a>'
                              for r in lst) + "</p>")
    blocks += (f'<p><a href="../{t["type"]}/index.html">'
               f'all {labels.get(t["type"], t["type"])}</a></p>')
    desc = (f"{t['tag']} on rule34.xxx: share of posts by year, peak {peak:.2f}% "
            f"in {peak_y}, now {cur:.2f}%.")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_escape(t['tag'])} — popularity by year | r34 tag trends</title>
<meta name="description" content="{html_escape(desc)}">
<link rel="canonical" href="{base}/tag/{slugs[t['tag']]}.html">
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
<h1>{html_escape(t['tag'])}</h1>
<p class="type"><span data-i18n="type">type</span>: {t['type']}</p>
{spark(vals, dyears, color)}
<p><span class="k" data-i18n="peak">peak</span>: {peak:.2f}% {peak_y} &nbsp;
<span class="k" data-i18n="now">now</span>: {cur:.2f}% &nbsp;
<span class="k" data-i18n="trend">trend</span>: {tr}× &nbsp;
<span class="k" data-i18n="aish">AI</span>: {(t['ai'] * 100):.1f}%
<svg width="120" height="7" style="vertical-align:middle">
<rect width="120" height="7" fill="#222"/>
<rect width="{t['ai'] * 120:.0f}" height="7" fill="#888"/>
</svg> &nbsp;
<span class="k" data-i18n="pm">±</span>: {(t['margin'] * 100):.1f}</p>
<table><tr><th data-i18n="year">year</th><th>%</th><th>n</th></tr>{rows}</table>
<p><span class="k" data-i18n="related">related</span>:</p>
{blocks}
<p><span class="k" data-i18n="badge">badge</span>:
<code>&lt;img src="{base}/badge/{slugs[t['tag']]}.svg"&gt;</code></p>
<p class="k" data-i18n="ainote">AI share</p>
<footer data-i18n="foot"> </footer>
</body></html>"""


def index_page(rows, title, base, dirname, note="", default_sort="total"):
    body = "".join(
        f'<tr data-total="{r["total"]}" data-ai="{r["ai"]}" data-trend="{r["trend"]}">'
        f'<td><a href="../tag/{slug(r["tag"])}.html">{html_escape(r["tag"])}</a></td>'
        f'<td>{r["total"]}</td><td>{(r["ai"] * 100):.0f}</td><td>{r["trend"]}×</td></tr>'
        for r in rows)
    opts = "".join(
        f'<option value="{v}"{" selected" if v == default_sort else ""}>{lab}</option>'
        for v, lab in (("total", "by volume"), ("ai", "by AI share"), ("trend", "by rise")))
    note_html = f'<p class="k">{note}</p>' if note else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{title} — r34 tag trends</title>
<meta name="description" content="{title} on rule34.xxx by year: volume, AI share and trend.">
<link rel="canonical" href="{base}/{dirname}/">
<script src="../i18n.js"></script>
<style>
 body{{background:#111;color:#ddd;font:13px system-ui;padding:24px;max-width:760px}}
 a{{color:#6aa8e8}} table{{border-collapse:collapse;margin-top:14px}}
 td,th{{padding:2px 10px;text-align:left;font-weight:400;border-bottom:1px solid #222}}
 select{{background:#1b1b1b;color:#ddd;border:1px solid #444;padding:2px}}
 .k{{color:#888}}
</style></head><body>
<p><a href="../" data-i18n="dash">← dashboard</a> · <a href="../tag/" data-i18n="tags">all tags</a></p>
<h1>{title}</h1>{note_html}
<p>sort: <select id="s">{opts}</select></p>
<table><thead><tr><th>tag</th><th>posts</th><th>AI %</th><th>trend</th></tr></thead>
<tbody id="tb">{body}</tbody></table>
<script>
document.getElementById('s').onchange=e=>{{
  const k=e.target.value, tb=document.getElementById('tb');
  [...tb.rows].sort((a,b)=>b.dataset[k]-a.dataset[k]).forEach(r=>tb.appendChild(r));
}};
</script></body></html>"""


def method(d, years, base):
    total = sum(d["n"].values())
    rows = "".join(f"<tr><td>{y}</td><td>{d['n'].get(y, 0)}</td></tr>" for y in years)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>methodology — r34 tag trends</title>
<meta name="description" content="How tag trends are computed: ID-to-date calibration, random sampling, confidence intervals, and known artifacts.">
<link rel="canonical" href="{base}/method.html">
<meta name="robots" content="index,follow">
<script src="i18n.js"></script>
<style>
 body{{background:#111;color:#ddd;font:14px system-ui;padding:24px;max-width:760px;line-height:1.65}}
 a{{color:#6aa8e8}} h1{{font-size:22px}} h2{{font-size:16px;margin-top:26px}}
 code{{color:#e0b23a}}
 table{{border-collapse:collapse}} td,th{{padding:2px 12px;border-bottom:1px solid #222;text-align:left}}
 button{{background:#1b1b1b;color:#ddd;border:1px solid #444;padding:2px 6px}}
</style></head><body>
<p><a href="./" data-i18n="dash">← dashboard</a>
 <button onclick="setLang(localStorage.lang==='en'?'ru':'en')">EN / RU</button></p>
<h1>Methodology</h1>
<p>This project measures what share of posts in each year carried a given tag.
Sample: <b>{total}</b> posts, {years[0]}–{years[-1]}.</p>

<h2>Where the year comes from</h2>
<p>The rule34.xxx API exposes no upload date. The only timestamp in a post object is
<code>change</code>, the time of the last edit, and it is always greater than or equal
to the upload time. Posts are sorted by ID and IDs grow monotonically, so the year is
reconstructed from the ID: ID windows are matched against the minimum <code>change</code>
in the window, the series is smoothed monotonically (pool-adjacent-violators), and each
post is then assigned to a year by interpolation.</p>
<p>This is an <b>estimate</b>. Retagging old posts drags it forward, and at year
boundaries the error can reach several months.</p>

<h2>Sampling</h2>
<p>ID windows are drawn at random across the whole range rather than walked in order,
to avoid bias towards recent uploads. Sample size per year:</p>
<table><tr><th>year</th><th>posts</th></tr>{rows}</table>
<p>Early years are thin: there were fewer uploads before 2014, and a random sample
rarely lands there. The left edge of every chart is noisy, and those shares are a
rough guide, not a measurement.</p>

<h2>Margin of error</h2>
<p>The “±” column is a 95% confidence interval computed as
<code>1.96·√(p(1−p)/n)</code> over the last three years. At a 10% share and n=3000
that is ±1.1 pp. A difference smaller than the interval is not a signal.</p>

<h2>Artifacts</h2>
<p>The “jump” column is the largest one-year rise in share. Values above 8 are dropped:
that profile means a tag was introduced or retagged in bulk, not that tastes shifted.
Example — <code>genitals</code>: 0.4% in 2020 and 22% in 2021, a 54-fold rise.</p>
<p>Gradual changes in tagging convention slip past the filter. The fall of
<code>human</code> mostly means people stopped listing the species, not that fewer
humans appear in the images.</p>

<p>Everything before 2011 is a single bucket marked ≤. Below roughly ID 120 000 the
date cannot be resolved: the oldest posts were mass-retagged, so their
<code>change</code> timestamps sit years after upload. Treat the first column as one
baseline, not as a year to compare with its neighbours.</p>

<h2>Aliases</h2>
<p>Duplicate spellings (<code>hi_res</code> / <code>highres</code>,
<code>ai-generated</code> / <code>ai_generated</code>) are merged before counting.
The map is partly auto-detected and partly hand-written, and merged tags inherit the
sum of their variants — so a rise there can come from the merge itself.</p>

<h2>What is not measured</h2>
<p>Share is neither quality nor views. <code>score</code> is useless for this: votes are
rare and values are 0 or 1. Deleted posts never enter the sample, so the history is
slightly censored by moderation. The <code>ai_generated</code> share is applied by hand,
so it understates the real figure.</p>

<h2>Data and license</h2>
<p>Raw aggregates: <a href="data.json">data.json</a>. Code: MIT.
Data belongs to rule34.xxx and to uploaders. Unofficial project.</p>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://developer01234.github.io/r34-stat")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--related", type=int, default=6)
    ap.add_argument("--data", default="data.json")
    ap.add_argument("--out", default="tag")
    a = ap.parse_args()

    d = json.loads(Path(a.data).read_text(encoding="utf-8"))
    years = d["years"]
    tags = d["tags"][:a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    used, vecs, slugs = {}, {}, {}
    for t in tags:
        s = slug(t["tag"])
        while s in used and used[s] != t["tag"]:
            s += "_"
        used[s] = t["tag"]
        slugs[t["tag"]] = s
        vecs[t["tag"]] = [t["shares"].get(y, 0) for y in years]

    for t in tags:
        others = [o for o in tags if o["tag"] != t["tag"]]
        others.sort(key=lambda o: -corr(vecs[t["tag"]], vecs[o["tag"]]))
        rel = defaultdict(list)
        for o in others:
            cap = 6 if o["type"] == t["type"] else 4
            if len(rel[o["type"]]) < cap:
                rel[o["type"]].append(o["tag"])
        (out / f"{slugs[t['tag']]}.html").write_text(
            page(t, d, years, rel, a.base, slugs), encoding="utf-8")

    idx = "".join(f'<li><a href="{slugs[t["tag"]]}.html">{html_escape(t["tag"])}</a> '
                  f'<span class="k">{t["type"]}</span></li>' for t in tags)
    (out / "index.html").write_text(
        f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>all tags</title>
<script src="../i18n.js"></script>
<style>body{{background:#111;color:#ddd;font:14px system-ui;padding:24px}}
a{{color:#6aa8e8}} .k{{color:#777;font-size:11px}} li{{margin:3px 0}}</style>
<p><a href="../" data-i18n="dash">← dashboard</a>
<button onclick="setLang(localStorage.lang==='en'?'ru':'en')">EN / RU</button></p>
<h1 data-i18n="tags">all tags</h1><ul>{idx}</ul>""", encoding="utf-8")

    for typ in sorted({x["type"] for x in tags}):
        sub = sorted([x for x in tags if x["type"] == typ], key=lambda r: -r["total"])
        d_dir = Path(typ)
        d_dir.mkdir(parents=True, exist_ok=True)
        (d_dir / "index.html").write_text(
            index_page(sub, f"all {typ}", a.base, typ), encoding="utf-8")

    for name, subset, label in [
        ("rising", [x for x in tags if x["trend"] > 1.5], "biggest risers"),
        ("falling", [x for x in tags if x["trend"] < 0.7], "biggest fallers"),
    ]:
        subset = [x for x in subset if x["margin"] < 0.05 and x["total"] >= 300]
        sub = sorted(subset, key=lambda r: (-r["trend"] if name == "rising" else r["trend"]))[:200]
        if not sub:
            continue
        d_dir = Path(name)
        d_dir.mkdir(parents=True, exist_ok=True)
        (d_dir / "index.html").write_text(
            index_page(sub, label, a.base, name, default_sort="trend",
                       note="trend = last 3 years vs first 3 years; "
                            "only tags with 300+ posts and a margin under 5 pp"),
            encoding="utf-8")

    (Path("method.html")).write_text(method(d, years, a.base), encoding="utf-8")

    bad = Path("badge")
    bad.mkdir(parents=True, exist_ok=True)
    for t in tags:
        (bad / f"{slugs[t['tag']]}.svg").write_text(badge(t, years), encoding="utf-8")

    (Path("slugs.json")).write_text(json.dumps(slugs, ensure_ascii=False),
                                    encoding="utf-8")

    redir = {}
    for t in tags:
        raw = t["tag"]
        if raw != slugs[raw] and re.fullmatch(r"[A-Za-z0-9._()!\[\]-]+", raw):
            redir[raw] = slugs[raw]

    keep_files = {f"{s}.html" for s in slugs.values()} | {"index.html"}
    keep_files |= {f"{r}.html" for r in redir}
    for f in out.glob("*.html"):
        if f.name not in keep_files:
            f.unlink()
    keep_badges = {f"{s}.svg" for s in slugs.values()}
    for f in bad.glob("*.svg"):
        if f.name not in keep_badges:
            f.unlink()
    for raw, target in redir.items():
        (out / f"{raw}.html").write_text(
            f'<!doctype html><meta charset="utf-8">'
            f'<meta http-equiv="refresh" content="0;url={target}.html">'
            f'<link rel="canonical" href="{a.base}/tag/{target}.html">',
            encoding="utf-8")

    urls = [f"{a.base}/", f"{a.base}/method.html", f"{a.base}/compare.html"]
    for name in ["tag", "badge", "artist", "character", "copyright",
                 "general", "metadata", "rising", "falling"]:
        p = Path(name)
        if p.is_dir():
            urls += [f"{a.base}/{name}/{x.name}" for x in sorted(p.glob("*.html"))]

    today = date.today().isoformat()
    (Path("sitemap.xml")).write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (Path("robots.txt")).write_text(
        f"User-agent: *\nAllow: /\nSitemap: {a.base}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(tags)} страниц + sitemap")


if __name__ == "__main__":
    main()