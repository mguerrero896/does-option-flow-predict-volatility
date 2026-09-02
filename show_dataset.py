"""Show the dataset an evaluator cannot otherwise see.

The raw feeds are licensed and cannot be redistributed, so nobody outside the project can
open them. That is a licensing fact, not a reason to leave the evaluator guessing about
whether the data exists or how large it is.

This prints the shape of the panel, the feature families that make it up, and a small
readable fragment -- enough to show the data is real and structured, without publishing a
single licensed row beyond a handful of cells already visible in the published artifacts.

    python show_dataset.py
"""
import glob
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
DATA_ROOTS = ["D:/MDS650/evidence_root/artifacts", "D:/MDS650", REPO]


def rule(title):
    print()
    print("=" * 78)
    print(f" {title}")
    print("=" * 78)


def find(pattern):
    for root in DATA_ROOTS:
        hits = glob.glob(os.path.join(root, pattern), recursive=True)
        if hits:
            return sorted(hits, key=lambda p: -os.path.getsize(p))[0]
    return None


try:
    import polars as pl
except ImportError:
    print("polars is not installed in this interpreter. Run with:")
    print('  uv run python show_dataset.py')
    sys.exit(1)

# ------------------------------------------------------------ 1. the panels
rule("1 - THE PANELS THIS STUDY IS BUILT ON")
PANELS = [
    ("B1 option-price features", "**/b1v3_features.parquet"),
    ("B2 option-flow mechanism", "**/b2_mechanism_forecasts.parquet"),
]
found = []
for label, pattern in PANELS:
    path = find(pattern)
    if not path:
        print(f"  {label:32} not found on this machine")
        continue
    lf = pl.scan_parquet(path)
    schema = lf.collect_schema()
    rows = lf.select(pl.len()).collect().item()
    size_mb = os.path.getsize(path) / 1e6
    found.append((label, path, schema, rows))
    print(f"  {label}")
    print(f"    file      {path}")
    print(f"    rows      {rows:,}")
    print(f"    columns   {len(schema.names())}")
    print(f"    on disk   {size_mb:,.1f} MB")
    print()

if not found:
    print("  No panel found. The licensed store may not be mounted.")
    sys.exit(0)

# --------------------------------------------------- 2. what the columns are
rule("2 - WHAT THE COLUMNS ACTUALLY ARE")
label, path, schema, rows = found[0]
names = schema.names()
print(f"  {label} -- {len(names)} columns\n")
KEYS = [n for n in names if n in ("session_date", "symbol", "asset", "date", "ts", "forecast_origin")]
feats = [n for n in names if n not in KEYS]
if KEYS:
    print(f"  keys ({len(KEYS)}):     {', '.join(KEYS)}")
print(f"  features ({len(feats)}):")
for i in range(0, len(feats), 3):
    print("    " + "".join(f"{n[:24]:26}" for n in feats[i:i + 3]))

# ------------------------------------------------------- 3. a real fragment
rule("3 - A FRAGMENT, SO YOU CAN SEE IT IS REAL DATA")
show = (KEYS[:2] + feats[:5])[:7]
frag = pl.scan_parquet(path).select(show).head(8).collect()
# ASCII_FULL, not the default box-drawing set: the Windows console is cp1252 and cannot
# encode the Unicode borders, which crashes the print rather than degrading it.
with pl.Config(tbl_rows=10, tbl_cols=10, fmt_str_lengths=18, tbl_width_chars=118,
               set_tbl_formatting="ASCII_FULL"):
    print(frag)
print(f"\n  8 rows of {rows:,}. {len(show)} columns of {len(names)}.")

# ------------------------------------------------------------ 4. the totals
rule("4 - THE DIMENSION OF THE WHOLE THING")
total_cells = 0
for label, path, schema, rows in found:
    cells = rows * len(schema.names())
    total_cells += cells
    print(f"  {label:32} {rows:>10,} rows x {len(schema.names()):>3} cols = {cells:>14,} values")
print(f"  {'':32} {'':>10}   {'':>3}         {total_cells:>14,} values in total")

ptr = os.path.join(REPO, "data", "GATED_DATA_POINTERS.json")
if os.path.exists(ptr):
    p = json.load(io.open(ptr, encoding="utf-8"))
    files = p if isinstance(p, list) else p.get("files", p)
    n = len(files)
    print()
    print(f"  The licensed store holds {n} derived files. Every one has its SHA-256 committed")
    print("  to the public repository, so the chain of custody is verifiable without the data.")

rule("WHY YOU CANNOT DOWNLOAD THIS")
print("  Three provider agreements -- Unusual Whales, Financial Modeling Prep, Massive --")
print("  forbid redistributing derived data. The panels stay on the licensed store.")
print()
print("  What IS public: every method, every test, every hash, and the full result set.")
print("  A stranger with no licence reproduces the entire chain on synthetic data.")
print()
