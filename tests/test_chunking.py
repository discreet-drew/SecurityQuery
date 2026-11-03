from secquery.chunking import chunk_pages
from secquery.models import Page


def test_chunk_length_limit_and_overlap():
    page = Page("doc", "security.pdf", 1, "0123456789" * 110)
    chunks = chunk_pages([page], chunk_size=80, overlap=15)
    assert chunks
    assert all(len(chunk.text) <= 80 for chunk in chunks)
    for left, right in zip(chunks, chunks[1:], strict=False):
        assert left.text[-15:] == right.text[:15]


def test_page_number_preserved_and_pages_never_merged():
    pages = [Page("doc", "a.pdf", 1, "A" * 100), Page("doc", "a.pdf", 2, "B" * 100)]
    chunks = chunk_pages(pages, chunk_size=40, overlap=5)
    assert {chunk.page_number for chunk in chunks if "A" in chunk.text} == {1}
    assert {chunk.page_number for chunk in chunks if "B" in chunk.text} == {2}
    assert all(not ("A" in chunk.text and "B" in chunk.text) for chunk in chunks)


def test_no_text_is_lost_from_nonempty_page():
    text = "abcdefghijklmnopqrstuvwxyz" * 50
    page = Page("doc", "a.pdf", 1, text)
    chunks = chunk_pages([page], chunk_size=100, overlap=20)
    ranges = sorted((chunk.metadata["start_char"], chunk.metadata["end_char"]) for chunk in chunks)
    assert ranges[0][0] == 0
    assert ranges[-1][1] == len(text)
    assert all(chunk.text == text[chunk.metadata["start_char"]:chunk.metadata["end_char"]] for chunk in chunks)
    assert all(left[1] - 20 == right[0] for left, right in zip(ranges, ranges[1:], strict=False))


def test_text_without_spaces_terminates_and_covers_input():
    text = "A" * 1600
    chunks = chunk_pages([Page("doc", "a.pdf", 1, text)], chunk_size=800, overlap=150)
    assert [len(chunk.text) for chunk in chunks] == [800, 800, 300]
    assert chunks[-1].metadata["end_char"] == len(text)
