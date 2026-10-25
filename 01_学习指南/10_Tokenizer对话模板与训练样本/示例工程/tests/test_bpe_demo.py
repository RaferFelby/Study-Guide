from itertools import product

import pytest

from bpe_demo import (
    build_vocab,
    count_pairs,
    decode_bpe,
    encode_bpe,
    merge_pair,
    train_merges,
)


def test_training_uses_corpus_frequency_and_has_deterministic_tie_break():
    merges = train_merges(["low", "low", "lower"], 4)
    assert merges == [(108, 111), (256, 119)]
    assert encode_bpe("lower", merges) == [257, 101, 114]
    assert build_vocab(merges)[257] == b"low"


def test_encoding_new_text_does_not_train_again_or_modify_rules():
    merges = train_merges(["low", "low", "lower"], 4)
    before = merges.copy()
    assert encode_bpe("lowest", merges) == [257, 101, 115, 116]
    assert encode_bpe("zzzzzz", merges) == [122] * 6
    assert merges == before


def test_overlapping_pair_counts_differ_from_nonoverlapping_replacements():
    sequence = [97, 97, 97]
    assert count_pairs([sequence]) == {(97, 97): 2}
    assert merge_pair(sequence, (97, 97), 256) == [256, 97]
    assert sequence == [97, 97, 97]


def test_training_does_not_merge_across_distinct_texts():
    assert train_merges(["a", "b", "a", "b"], 10) == []
    assert train_merges(["ab", "ab"], 10) == [(97, 98)]


@pytest.mark.parametrize("text", ["", "a", "猫🙂", "a b\na\tb", "é", "e\u0301", "\x00"])
def test_round_trip_preserves_unicode_whitespace_and_empty_text(text):
    merges = train_merges([text, text], 8)
    assert decode_bpe(encode_bpe(text, merges), merges) == text


def test_all_short_binary_texts_round_trip_and_do_not_expand():
    texts = [
        "".join(chars) for size in range(6) for chars in product("ab", repeat=size)
    ]
    merges = train_merges(texts, 12)
    for text in texts:
        token_ids = encode_bpe(text, merges)
        assert len(token_ids) <= len(text.encode("utf-8"))
        assert decode_bpe(token_ids, merges) == text


def test_zero_budget_empty_corpus_and_singletons_stop_cleanly():
    assert train_merges(["aaa"], 0) == []
    assert train_merges([], 10) == []
    assert train_merges(["", "x", "y"], 10) == []
    assert train_merges(["abc"], 10) == []


@pytest.mark.parametrize("budget", [-1, True, 2.5])
def test_invalid_merge_budget(budget):
    with pytest.raises(ValueError):
        train_merges(["ab"], budget)


@pytest.mark.parametrize("corpus", ["ab", ["ab", 2]])
def test_invalid_training_input(corpus):
    with pytest.raises(TypeError):
        train_merges(corpus, 2)


@pytest.mark.parametrize(
    "rules", [[(256, 97)], [(97, 98), (97, 98)], [(True, 97)], [(97,)], [[97, 98]]]
)
def test_invalid_rules_are_rejected(rules):
    with pytest.raises(ValueError):
        encode_bpe("ab", rules)


@pytest.mark.parametrize("token_ids", [[999], [-1], [True], [1.5]])
def test_invalid_token_ids_are_rejected(token_ids):
    with pytest.raises(ValueError):
        decode_bpe(token_ids, [])


def test_incomplete_utf8_is_rejected_instead_of_silently_replaced():
    with pytest.raises(UnicodeDecodeError):
        decode_bpe([231], [])


def test_training_input_is_unchanged():
    corpus = ["low", "low", "lower"]
    train_merges(corpus, 10)
    assert corpus == ["low", "low", "lower"]
