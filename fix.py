M = {
    "\u0413\u2014": "\u00d7",
    "\u0412\u00b7": "\u00b7",
    "\u0412\u00b1": "\u00b1",
    "\u0432\u2020\u0452": "\u2190",
    "\u0432\u2020\u2019": "\u2192",
    "\u0432\u0402\u201c": "\u2013",
    "\u0432\u0402\u201d": "\u2014",
}

def load(p):
    b = open(p, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "cp1251"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace"), "replace"

for p in ["r34/pages.py", "r34/aggregate.py", "r34/harvest.py", "r34/calibrate.py",
          "i18n.js", "index.html", "compare.html", "README.md", "method.html",
          "sitemap.xml", "robots.txt"]:
    try:
        s, enc = load(p)
    except FileNotFoundError:
        continue
    t = s
    for a, b in M.items():
        t = t.replace(a, b)
    if s != t or enc not in ("utf-8", "utf-8-sig"):
        open(p, "w", encoding="utf-8", newline="\n").write(t)
        print(p, "->", enc, "-> utf-8", "| замен:", len(s) - len(t) and "да" or "нет")
