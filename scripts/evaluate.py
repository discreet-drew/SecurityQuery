from __future__ import annotations
import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secquery.baseline import answer_without_retrieval  
from secquery.config import Settings  
from secquery.pipeline import SecQuery  

FIELDS = ["question_id", "category", "condition", "question", "answer", "abstained", "latency_seconds", "notes", "correct", "faithful", "citation_supported"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=ROOT / "eval" / "questions.json")
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "results" / "evaluation.csv")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    settings = Settings.load(ROOT / ".env")
    engine = SecQuery(settings)
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if args.limit:
        questions = questions[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing: set[tuple[str, str]] = set()
    if args.output.exists():
        with args.output.open(newline="", encoding="utf-8") as handle:
            existing = {(row["question_id"], row["condition"]) for row in csv.DictReader(handle)}
    needs_header = not args.output.exists() or args.output.stat().st_size == 0
    with args.output.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if needs_header:
            writer.writeheader()
        for item in questions:
            for condition in ("llm_only", "vector_only", "hybrid_verified"):
                key = (str(item["id"]), condition)
                if key in existing:
                    continue
                start = time.perf_counter()
                try:
                    if condition == "llm_only":
                        answer = answer_without_retrieval(item["question"], engine.llm)
                        abstained = False
                        notes = "Unverified, context-free baseline; never use as advice."
                    elif condition == "vector_only":
                        result = engine.ask_vector_only(item["question"])
                        answer = result.answer
                        abstained = result.abstained
                        notes = result.reason
                    else:
                        result = engine.ask(item["question"])
                        answer = result.answer
                        abstained = result.abstained
                        notes = result.reason
                    latency = time.perf_counter() - start
                except Exception as exc:
                    answer, abstained, notes = "", True, f"ERROR: {exc}"
                    latency = time.perf_counter() - start
                writer.writerow({
                    "question_id": item["id"], "category": item.get("category", "unknown"),
                    "condition": condition, "question": item["question"], "answer": answer,
                    "abstained": str(abstained).lower(), "latency_seconds": f"{latency:.4f}",
                    "notes": notes, "correct": "", "faithful": "", "citation_supported": "",
                })
                handle.flush()
                existing.add(key)
                print(f"{item['id']} {condition}: {latency:.2f}s")
    print(f"Saved resumable evaluation to {args.output}. Fill scoring columns manually or with a blinded rubric.")


if __name__ == "__main__":
    main()
