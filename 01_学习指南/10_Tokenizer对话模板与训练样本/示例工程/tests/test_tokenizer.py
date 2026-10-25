import pytest

from tokenizer import BYTE_OFFSET, decode_ids, encode_text


def test_utf8_byte_fallback_round_trips_chinese_and_emoji():
    text = "你好，tokenizer 🙂"

    assert decode_ids(encode_text(text)) == text
    assert all(
        BYTE_OFFSET <= token_id <= BYTE_OFFSET + 255 for token_id in encode_text(text)
    )


def test_decode_shows_special_tokens_and_byte_text():
    assert decode_ids([1, *encode_text("A"), 2]) == "<|bos|>A<|eos|>"


def test_encode_rejects_non_string():
    with pytest.raises(TypeError, match="字符串"):
        encode_text(12)


def test_decode_rejects_unknown_id():
    with pytest.raises(ValueError, match="未知 token ID"):
        decode_ids([999])


def test_decode_rejects_incomplete_utf8_sequence():
    with pytest.raises(UnicodeDecodeError):
        decode_ids([BYTE_OFFSET + 0xE4])
