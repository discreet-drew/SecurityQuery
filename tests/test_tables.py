from secquery.tables import row_to_text

def test_row_to_text_normalizes_cells_and_joins_with_pipe():
    assert row_to_text(["  CVE-2024-12345 ", "fixed\nversion", None, "4.2.8"]) == "CVE-2024-12345 | fixed version | 4.2.8"


def test_empty_row_returns_empty_string():
    assert row_to_text([None, "", "  "]) == ""


def test_each_table_row_gets_its_own_chunk_and_long_rows_are_bounded():
    from secquery.tables import rows_to_chunks

    chunks = rows_to_chunks(
        [(2, ["CVE-2024-12345", "A" * 60]), (2, ["Version", "4.2.8"])],
        document_id="doc",
        document_name="advisory.pdf",
        chunk_size=40,
        overlap=5,
    )
    assert chunks
    assert all(chunk.page_number == 2 for chunk in chunks)
    assert all(chunk.metadata["kind"] == "table_row" for chunk in chunks)
    assert all(len(chunk.text) <= 40 for chunk in chunks)
    assert len({chunk.metadata["row_index"] for chunk in chunks}) == 2
