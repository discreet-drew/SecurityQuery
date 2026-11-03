from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secquery.build import IndexBuilder  
from secquery.config import Settings  


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="Re-embed all documents")
    parser.add_argument("--directory", type=Path, default=ROOT / "data" / "pdfs")
    args = parser.parse_args()
    settings = Settings.load(ROOT / ".env")
    builder = IndexBuilder(settings)
    if args.rebuild:
        builder.rebuild()
    paths = sorted(args.directory.glob("*.pdf")) if args.directory.exists() else []
    for path in paths:
        try:
            doc_id = builder.add_document(path)
            print(f"Indexed {path.name}: {doc_id}")
        except Exception as exc:
            print(f"FAILED {path.name}: {exc}")
    print(f"Done. Documents={len(builder.store.list_documents())}; chunks={len(builder.store.list_chunks())}")


if __name__ == "__main__":
    main()
