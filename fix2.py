R = [
    ("1.96\u00b7\u0432\u20ac\u0459(p(1\u0432\u20ac\u2019p)/n)",
     "1.96\u00b7\u221a(p(1\u2212p)/n)"),
    ("\u0432\u0402\u045ajump\u0432\u0402\u045c", "\u201cjump\u201d"),
]
p = "r34/pages.py"
s = open(p, encoding="utf-8").read()
for a, b in R:
    s = s.replace(a, b)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
