from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secquery.config import Settings  
from secquery.hybrid import hybrid_search  
from secquery.pipeline import SecQuery  


def main() -> None:
    settings = Settings.load(ROOT / ".env")
    engine = SecQuery(settings)
    question_file = ROOT / "eval" / "dev_questions.json"
    questions = json.loads(question_file.read_text(encoding="utf-8"))
    scores = {"answerable": [], "unanswerable": []}
    for item in questions:
        hits = hybrid_search(
            item["question"], embedder=engine.embedder, vector_index=engine.index, store=engine.store,
            top_k_vector=settings.top_k_vector, top_k_lexical=settings.top_k_lexical,
            top_k_final=settings.top_k_final, rrf_k=settings.rrf_k,
            exact_id_boost=settings.exact_id_boost,
        )
        group = "answerable" if item.get("answerable", True) else "unanswerable"
        scores[group].append(hits[0].score if hits else 0.0)
        print(f"{group:13s} max_score={scores[group][-1]:.4f} question={item['question']}")
    for group, values in scores.items():
        if values:
            print(f"{group}: n={len(values)} min={min(values):.4f} median={sorted(values)[len(values)//2]:.4f} max={max(values):.4f}")
    print("Tune SECQUERY_MIN_RETRIEVAL_SCORE against held-out development data only; do not tune on eval/questions.json.")


if __name__ == "__main__":
    main()
