from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, nargs="?", default=ROOT / "eval" / "results" / "evaluation.csv")
    args = parser.parse_args()
    if not args.csv_path.exists():
        raise SystemExit(f"No results file found at {args.csv_path}. Run scripts/evaluate.py first.")
    data = pd.read_csv(args.csv_path)
    data["latency_seconds"] = pd.to_numeric(data["latency_seconds"], errors="coerce")
    aggregations: dict[str, tuple[str, str]] = {"n": ("question_id", "count"), "mean_latency": ("latency_seconds", "mean"), "p95_latency": ("latency_seconds", lambda x: x.quantile(0.95))}
    for name in ("correct", "faithful", "citation_supported"):
        if name in data:
            values = data[name].astype(str).str.lower().map({"true": 1, "false": 0, "1": 1, "0": 0, "yes": 1, "no": 0})
            data[f"_{name}_numeric"] = values
            aggregations[f"{name}_rate"] = (f"_{name}_numeric", "mean")
    summary = data.groupby("condition", dropna=False).agg(**aggregations).reset_index()
    print(summary.to_string(index=False))
    category_cols = ["correct", "faithful", "citation_supported"]
    available = [col for col in category_cols if col in data and data[col].notna().any()]
    if available:
        print("\nPer-category scoring:")
        print(data.groupby(["category", "condition"])[available].agg("count").to_string())
    out = args.csv_path.with_name(args.csv_path.stem + "_summary.csv")
    summary.to_csv(out, index=False)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
