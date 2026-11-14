from rx.textutil import (analyze, count_tokens, fold, split_sentences,
                         stem, tokenize)


def test_fold_lowercases_and_strips_accents():
    assert fold("Café NAÏVE") == "cafe naive"


def test_tokenize_keeps_codes_and_their_parts():
    tokens = tokenize("Lot H-2291 failed SPEC-112 §4.2 at 2.0%.")
    assert "h-2291" in tokens and "2291" in tokens and "h" in tokens
    assert "spec-112" in tokens and "4.2" in tokens and "2.0" in tokens


def test_analyze_drops_stopwords_and_stems_plurals():
    assert analyze("The castings of the lots") == ["casting", "lot"]


def test_stem_is_tiny_on_purpose():
    assert stem("bearings") == "bearing"
    assert stem("properties") == "property"
    assert stem("glass") == "glass"
    assert stem("h-2291") == "h-2291"


def test_count_tokens_is_words_times_1_3():
    assert count_tokens("one two three four five six seven") == 9
    assert count_tokens("") == 0


def test_split_sentences():
    text = "Tensile was 312 MPa. Porosity 2.0% passed!\n\nNext para"
    assert split_sentences(text) == [
        "Tensile was 312 MPa.", "Porosity 2.0% passed!", "Next para"]
