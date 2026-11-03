from secquery.models import Chunk
from secquery.verify import normalize, verified


def test_fake_quote_is_rejected():
    chunk = Chunk("d", "a.pdf", 1, "c1", "Upgrade the gateway to version 4.2.8.")
    assert not verified("The vendor confirms a patch in 5.0.", chunk)


def test_whitespace_and_unicode_normalization_are_tolerated():
    chunk = Chunk("d", "a.pdf", 1, "c1", "Upgrade   the gateway\nto version 4.2.8.")
    assert verified("Upgrade the gateway to version 4.2.8.", chunk)
    assert normalize("A\t B") == "a b"
