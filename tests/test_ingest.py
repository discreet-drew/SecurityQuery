from __future__ import annotations
import pytest
from secquery.ingest import PDFIngestError, pdf_to_pages


def test_pdf_ingestion_preserves_one_based_pages_and_blank_pages(tmp_path, make_pdf):
    path = make_pdf(tmp_path / "tiny.pdf", ["Page one security note", "", "Page three CVE-2024-12345"])
    pages = pdf_to_pages(path)
    assert len(pages) == 3
    assert [page.page_number for page in pages] == [1, 2, 3]
    assert pages[0].has_text
    assert not pages[1].has_text
    assert "CVE-2024-12345" in pages[2].text


def test_pdf_page_cap_is_enforced(tmp_path, make_pdf):
    path = make_pdf(tmp_path / "tiny.pdf", ["one", "two"])
    with pytest.raises(PDFIngestError, match="maximum"):
        pdf_to_pages(path, max_pages=1)
