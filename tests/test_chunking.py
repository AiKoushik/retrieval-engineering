import pytest

from rx.chunking import Chunk, fixed_chunks


def words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


def test_offsets_point_back_into_the_text():
    text = "alpha  beta\ngamma " + words(500)
    for chunk in fixed_chunks("d", text, size=64, overlap=13):
        assert text[chunk.start:chunk.end] == chunk.text


def test_windows_have_fixed_size_and_overlap():
    chunks = fixed_chunks("d", words(400), size=130, overlap=26)
    # 130 tokens / 1.3 = 100 words; 26 / 1.3 = 20 words shared
    assert [len(c.text.split()) for c in chunks[:-1]] == [100] * 4
    assert chunks[0].text.split()[-20:] == chunks[1].text.split()[:20]
    assert chunks[-1].text.endswith("w399")


def test_ids_and_short_and_empty_texts():
    (only,) = fixed_chunks("TR-1", "short text")
    assert only == Chunk("TR-1", 0, "short text", 0, 10)
    assert only.chunk_id == "TR-1#0"
    assert fixed_chunks("x", "   ") == []


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        fixed_chunks("d", "text", size=10, overlap=10)
