"""标准库实现的小规模字节 BPE；与对话模板使用的 tokenizer 分开。"""

BYTE_VOCAB_SIZE = 256


def count_pairs(sequences: list[list[int]]) -> dict[tuple[int, int], int]:
    counts = {}
    for sequence in sequences:
        for index in range(len(sequence) - 1):
            pair = (sequence[index], sequence[index + 1])
            counts[pair] = counts.get(pair, 0) + 1
    return counts


def merge_pair(sequence: list[int], pair: tuple[int, int], new_id: int) -> list[int]:
    """从左向右非重叠替换；返回新列表，不改传入序列。"""
    merged = []
    index = 0
    while index < len(sequence):
        if index + 1 < len(sequence) and (sequence[index], sequence[index + 1]) == pair:
            merged.append(new_id)
            index += 2
        else:
            merged.append(sequence[index])
            index += 1
    return merged


def train_merges(texts: list[str], max_merges: int) -> list[tuple[int, int]]:
    """每轮合并最频繁的相邻对；本教学约定频次不足 2 时停止。"""
    if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
        raise TypeError("texts 必须是字符串列表")
    if type(max_merges) is not int or max_merges < 0:
        raise ValueError("max_merges 必须是非负整数")
    sequences = [list(text.encode("utf-8")) for text in texts]
    merges = []
    for _ in range(max_merges):
        counts = count_pairs(sequences)
        if not counts:
            break
        # 相同频次时，选择 ID 对字典序最小者，使本实验结果可复查。
        best_pair = min(counts, key=lambda pair: (-counts[pair], pair))
        if counts[best_pair] < 2:
            break
        new_id = BYTE_VOCAB_SIZE + len(merges)
        sequences = [merge_pair(sequence, best_pair, new_id) for sequence in sequences]
        merges.append(best_pair)
    return merges


def build_vocab(merges: list[tuple[int, int]]) -> dict[int, bytes]:
    """还原各 token 的字节串，并检查规则只能引用已经存在的 ID。"""
    if not isinstance(merges, list):
        raise TypeError("合并规则必须是列表")
    vocab = {value: bytes([value]) for value in range(BYTE_VOCAB_SIZE)}
    seen_pairs = set()
    for pair in merges:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValueError("每条规则必须是包含两个 ID 的元组")
        if any(type(token_id) is not int or token_id not in vocab for token_id in pair):
            raise ValueError("合并规则引用了未知或未来 ID")
        if pair in seen_pairs:
            raise ValueError("合并规则不能重复")
        new_id = len(vocab)
        vocab[new_id] = vocab[pair[0]] + vocab[pair[1]]
        seen_pairs.add(pair)
    return vocab


def encode_bpe(text: str, merges: list[tuple[int, int]]) -> list[int]:
    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")
    build_vocab(merges)
    sequence = list(text.encode("utf-8"))
    for rank, pair in enumerate(merges):
        sequence = merge_pair(sequence, pair, BYTE_VOCAB_SIZE + rank)
    return sequence


def decode_bpe(token_ids: list[int], merges: list[tuple[int, int]]) -> str:
    vocab = build_vocab(merges)
    pieces = []
    for token_id in token_ids:
        if type(token_id) is not int or token_id not in vocab:
            raise ValueError("未知或非法 token ID")
        pieces.append(vocab[token_id])
    return b"".join(pieces).decode("utf-8")


def main() -> None:
    corpus = ["low", "low", "lower"]
    merges = train_merges(corpus, max_merges=4)
    vocab = build_vocab(merges)
    print("合并规则", merges)
    for rank, pair in enumerate(merges):
        token_id = BYTE_VOCAB_SIZE + rank
        print("新 token", token_id, pair, vocab[token_id])
    print(
        "训练文本总 token 数",
        sum(len(text.encode("utf-8")) for text in corpus),
        "→",
        sum(len(encode_bpe(text, merges)) for text in corpus),
    )
    for text in ("lower", "lowest", "猫🙂", ""):
        token_ids = encode_bpe(text, merges)
        print(repr(text), token_ids, "往返一致", decode_bpe(token_ids, merges) == text)


if __name__ == "__main__":
    main()
