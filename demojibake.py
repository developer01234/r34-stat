for p in ["r34/pages.py", "index.html", "compare.html", "i18n.js"]:
    try:
        src = open(p, encoding="utf-8").read().split("\n")
    except FileNotFoundError:
        continue
    out, n = [], 0
    for l in src:
        if any(ord(c) > 127 for c in l):
            try:
                fixed = l.encode("cp1251").decode("utf-8")
                if "\ufffd" not in fixed and fixed != l:
                    l = fixed
                    n += 1
            except UnicodeEncodeError:
                pass
            except UnicodeDecodeError:
                pass
        out.append(l)
    open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print(p, "строк исправлено:", n)
