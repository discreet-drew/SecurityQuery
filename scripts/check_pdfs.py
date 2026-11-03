from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secquery.ingest import PDFIngestError, pdf_to_pages  

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[ROOT / "data" / "pdfs"])
    args = parser.parse_args()
    pdfs = [path for entry in args.paths for path in (entry.rglob("*.pdf") if entry.is_dir() else [entry])]
    if not pdfs:
        print("No PDFs found.")
        return
    for path in sorted(pdfs):
        try:
            pages = pdf_to_pages(path)
            total = sum(len(page.text) for page in pages)
            populated = sum(page.has_text for page in pages)
            coverage = populated / max(1, len(pages))
            print(f"{path}: pages={len(pages)}, text_pages={populated}, coverage={coverage:.1%}, chars={total}")
            if coverage < 0.5:
                print("  REVIEW: likely scanned or image-heavy; OCR may be necessary.")
        except PDFIngestError as exc:
            print(f"ERROR {path}: {exc}")


if __name__ == "__main__":
    main()
