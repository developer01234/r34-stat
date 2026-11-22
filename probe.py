for p in ["r34/pages.py", "index.html", "compare.html", "i18n.js"]:
    try:
        for i, l in enumerate(open(p, encoding="utf-8"), 1):
            if any(ord(c) > 127 for c in l) and ("trend" in l or "fall" in l or "rise" in l or "\u00b7" in l or "\u0412" in l or "\u0413" in l):
                print(p, i, ascii(l.strip()[:160]))
    except FileNotFoundError:
        pass
