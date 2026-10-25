"""用于教学的 UTF-8 字节回退 tokenizer，不是生产级子词 tokenizer。"""

from collections.abc import Iterable

PAD_ID = 0
BOS_ID = 1
EOS_ID = 2
IM_START_ID = 3
IM_SEP_ID = 4
IM_END_ID = 5
BYTE_OFFSET = 6

SPECIAL_TOKENS = {
    PAD_ID: "<|pad|>",
    BOS_ID: "<|bos|>",
    EOS_ID: "<|eos|>",
    IM_START_ID: "<|im_start|>",
    IM_SEP_ID: "<|im_sep|>",
    IM_END_ID: "<|im_end|>",
}


def encode_text(text: str) -> list[int]:
    """把文本编码为 UTF-8 字节 ID；每个字节对应一个 ID。"""
    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")
    return [BYTE_OFFSET + value for value in text.encode("utf-8")]


def decode_ids(token_ids: Iterable[int]) -> str:
    """解码字节 ID，并把特殊 ID 显示为可读拼写。"""
    pieces: list[str] = []
    pending_bytes = bytearray()

    def flush_bytes() -> None:
        if pending_bytes:
            pieces.append(pending_bytes.decode("utf-8"))
            pending_bytes.clear()

    for token_id in token_ids:
        if not isinstance(token_id, int):
            raise TypeError("token ID 必须是整数")
        if BYTE_OFFSET <= token_id <= BYTE_OFFSET + 255:
            pending_bytes.append(token_id - BYTE_OFFSET)
        elif token_id in SPECIAL_TOKENS:
            flush_bytes()
            pieces.append(SPECIAL_TOKENS[token_id])
        else:
            raise ValueError(f"未知 token ID：{token_id}")

    flush_bytes()
    return "".join(pieces)
