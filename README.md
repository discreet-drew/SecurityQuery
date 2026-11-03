# SecQuery — Cybersecurity Document Intelligence Assistant

SecQuery is a local-first prototype for asking questions over cybersecurity PDFs, extracting structured vulnerability/advisory fields, verifying quoted evidence, and comparing multiple documents. It is designed around **document-grounded answers**, source-page citations, explicit gaps, and cautious abstention.

> **Prototype disclaimer:** SecQuery is not a live vulnerability scanner, SIEM, exploitability checker, or a substitute for security review. It cannot determine whether a real system is compromised from PDFs alone. Synthetic CVEs and sample recommendations are fictional test fixtures and must never be used operationally.

## Architecture

```text
PDFs -> PyMuPDF pages + pdfplumber table rows -> page-bounded overlapping chunks
     -> entity extraction -> SQLite metadata/chunks + Sentence Transformer embeddings
     -> FAISS cosine-like search + BM25 lexical search -> RRF and exact-ID boost
     -> Ollama JSON generation -> quote verification -> answer/citations or abstention
```

SQLite is the source of truth for document and chunk metadata. A FAISS index is saved alongside an ID sidecar (or a NumPy fallback is used if FAISS is unavailable). On load, SecQuery checks the vector index against SQLite and rebuilds it when item IDs disagree. Incremental additions are supported; deleting or replacing indexed documents should be followed by `IndexBuilder.rebuild()` to remove stale vectors.

## Requirements

- Python 3.10+ (CI uses Python 3.11)
- Ollama installed locally and a model downloaded, unless using only the tests
- A text-based PDF for initial testing. Scanned PDFs may need OCR; OCR is deliberately not automatic.
- FAISS is optional; the index wrapper falls back to NumPy when FAISS cannot be installed on your platform. To install the accelerator when supported, run `pip install -e .[faiss]`.

## Setup

From the repository root:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements.txt
copy .env.example .env     # Windows; on macOS/Linux use: cp .env.example .env
```

Edit `.env` as needed. The defaults use `sentence-transformers/all-MiniLM-L6-v2` (the first run may download model files) and the Ollama model `llama3.1:8b`. Start Ollama and obtain the configured model, for example:

```bash
ollama pull llama3.1:8b
ollama serve
```

Keep `.env`, real PDFs, embeddings, and the SQLite database out of Git. `.gitignore` is configured for the default data folders; check `git status` before every commit.

## Index PDFs

Put authorized, text-based PDFs in `data/pdfs/`, then run:

```bash
python scripts/check_pdfs.py
python scripts/build_index.py
```

Or launch the UI and upload a PDF through the Library tab:

```bash
streamlit run app/streamlit_app.py
```

The Library supports trust labels (`official`, `vendor`, `internal`, `synthetic`, `unreviewed`). Labels are metadata only and do not authenticate a publisher. Confirm source provenance independently.

## Core Python usage

```python
from secquery.pipeline import SecQuery

engine = SecQuery()
document_id = engine.add_document("data/pdfs/vendor-advisory.pdf", trust_level="vendor")
result = engine.ask("Which mitigation does the document explicitly recommend?")
print(result.answer)

fields = engine.extract_document(document_id, ["CVE ID", "affected versions", "fixed version", "CVSS score"])
for field_name, field in fields.items():
    print(field_name, field.value, field.verified, field.page_number)
```

The verified flag only means the exact supporting quote appeared in the cited retrieved chunk. It does **not** independently validate the factual accuracy or current status of the source document.

## Tests and lint

Tests use a deterministic offline hashing embedder and a fake LLM; they do not download a model or need Ollama.

```bash
SECQUERY_EMBEDDER_BACKEND=offline pytest
ruff check src app scripts tests
```

On Windows PowerShell, set environment variables with `$env:SECQUERY_EMBEDDER_BACKEND = "offline"`. Most tests inject the offline embedder directly and do not depend on environment state.

## Evaluation workflow

1. Add and index permitted reference materials and, if needed, create deliberately synthetic fixtures using `python scripts/make_synthetic.py`.
2. Tune thresholds with `python scripts/tune_threshold.py` using `eval/dev_questions.json` only.
3. Freeze `eval/questions.json` before looking at evaluation outcomes.
4. Run `python scripts/evaluate.py`; the CSV can be resumed if interrupted. The harness includes a context-free LLM-only baseline, a vector-only retriever, and the hybrid retrieval pipeline with quote verification. Both retrieval conditions share the same answer-generation and quote-checking path so the retrieval strategy is the main difference; the LLM-only condition is ungrounded and should be labeled accordingly.
5. Score answers using `eval/rubric.md`, fill the `correct`, `faithful`, and `citation_supported` columns, then run `python scripts/analyze_results.py`.

Report per-category performance, abstention quality, latency, and confidence intervals. Do not claim “hallucination-free.” Test retrieval recall separately from answer correctness. Use official source material and track its version/date/license in `data/sources.csv`. Verify the licensing terms before redistributing downloaded content.

## Data and safety notes

- `data/pdfs/`, `data/synthetic/`, `data/index/` and `eval/results/` are gitignored except for `.gitkeep` placeholders.
- PDF text is untrusted evidence. SecQuery's prompts tell the LLM not to obey instructions embedded in retrieved documents; prompt-injection tests are included, but this is not a complete security boundary.
- Do not upload secrets, private customer reports, or regulated data to a hosted model without authorization. If using internal documents, add authentication, access controls, encryption, audit logging, and document-level authorization before deploying to others.
- Entity extraction is a set of heuristic regular expressions. Version detection may have false positives/negatives; confirm all outputs.
- The source catalog is a starter list. Confirm source version, license, date, and integrity before use.

## Project layout

The repository follows the requested `src/secquery` package layout. `app/tabs` contains the four Streamlit tabs, `scripts/` contains ingestion/evaluation helpers, `eval/` stores development and frozen questions, and `tests/` covers the core pipeline. `controls.py` is a small starter mapping—not a compliance engine.
