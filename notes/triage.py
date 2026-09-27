import json

m = json.load(open("reports/metrics.json"))
cols = sorted({k.split(".")[1] for k in m if k.startswith("profile.") and k.count(".") == 2})

print(f"{'column':15}{'null%':>7}{'distinct':>9}{'len':>8}{'patterns':>9}{'top pattern share':>19}")
for c in cols:
    p = lambda s: m[f"profile.{c}.{s}"]
    share = p("top_patterns")[0]["count"] / p("total_rows")
    length = f"{p('min_length')}-{p('max_length')}"
    print(f"{c:15}{p('null_rate')*100:>6.1f}%{p('distinct_count'):>9}{length:>8}"
          f"{p('distinct_pattern_count'):>9}{share:>18.0%}")