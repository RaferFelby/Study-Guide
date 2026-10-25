import pytest

from chat_data import IGNORE_INDEX, count_supervised_tokens, encode_messages, pad_batch
from tokenizer import (
    BOS_ID,
    EOS_ID,
    IM_END_ID,
    IM_SEP_ID,
    IM_START_ID,
    PAD_ID,
    decode_ids,
    encode_text,
)


def sample_messages(user_text="hi", assistant_text="hello"):
    return [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": assistant_text},
    ]


def test_assistant_content_and_endings_are_supervised_but_user_is_masked():
    input_ids, labels = encode_messages(sample_messages())

    assert input_ids[0] == BOS_ID
    assert labels[0] == IGNORE_INDEX
    assert count_supervised_tokens(labels) == len(encode_text("hello")) + 2
    assert labels[-2:] == [IM_END_ID, EOS_ID]


def test_system_and_user_context_are_kept_as_input_but_not_supervised():
    messages = [
        {"role": "system", "content": "Be concise."},
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer"},
    ]
    input_ids, labels = encode_messages(messages)
    readable = decode_ids(input_ids)

    assert "Be concise." in readable
    assert "Question" in readable
    assert count_supervised_tokens(labels) == len(encode_text("Answer")) + 2


def test_tool_round_trip_contains_assistant_tool_and_tool_reply():
    messages = [
        {"role": "user", "content": "weather?"},
        {"role": "assistant", "recipient": "weather", "content": "query"},
        {"role": "tool", "content": "sunny"},
        {"role": "assistant", "content": "It is sunny."},
    ]
    input_ids, labels = encode_messages(messages)

    readable = decode_ids(input_ids)
    assert "assistant to=weather" in readable
    assert input_ids.count(IM_SEP_ID) == len(messages)
    assert count_supervised_tokens(labels) == (
        len(encode_text("query")) + len(encode_text("It is sunny.")) + 3
    )


def test_template_has_one_start_marker_per_message_and_single_bos():
    input_ids, _ = encode_messages(sample_messages())

    assert input_ids.count(BOS_ID) == 1
    assert input_ids.count(IM_START_ID) == 2


def test_right_padding_keeps_real_tokens_first_and_masks_padding():
    short = encode_messages(sample_messages("q", "a"))
    long = encode_messages(sample_messages("long question", "long answer"))

    batch = pad_batch([short, long], padding_side="right")
    short_size = len(short[0])

    assert batch["input_ids"][0][:short_size] == short[0]
    assert batch["attention_mask"][0] == [1] * short_size + [0] * (
        len(long[0]) - short_size
    )
    assert batch["labels"][0][short_size:] == [IGNORE_INDEX] * (
        len(long[0]) - short_size
    )


def test_left_padding_keeps_real_tokens_at_the_right_for_batched_generation():
    short = encode_messages(sample_messages("q", "a"))
    long = encode_messages(sample_messages("long question", "long answer"))

    batch = pad_batch([short, long], padding_side="left")
    padding_length = len(long[0]) - len(short[0])

    assert batch["input_ids"][0][:padding_length] == [PAD_ID] * padding_length
    assert batch["input_ids"][0][padding_length:] == short[0]
    assert batch["attention_mask"][0] == [0] * padding_length + [1] * len(short[0])
    assert batch["labels"][0][:padding_length] == [IGNORE_INDEX] * padding_length


def test_each_sample_has_supervision_and_padding_mask_is_not_loss_mask():
    examples = [
        encode_messages(sample_messages("one", "yes")),
        encode_messages(sample_messages("two", "ok")),
        encode_messages(
            [
                {"role": "system", "content": "brief"},
                {"role": "user", "content": "third"},
                {"role": "assistant", "content": "done"},
            ]
        ),
    ]
    batch = pad_batch(examples)

    assert all(count_supervised_tokens(labels) > 0 for _, labels in examples)
    assert all(
        mask_value == 1
        for mask_value in batch["attention_mask"][0][: len(examples[0][0])]
    )
    assert IGNORE_INDEX in batch["labels"][0]


@pytest.mark.parametrize("side", ["top", "middle", "both"])
def test_invalid_padding_side_is_rejected(side):
    example = encode_messages(sample_messages())

    with pytest.raises(ValueError, match="padding_side"):
        pad_batch([example], padding_side=side)


def test_mismatched_input_and_label_lengths_are_rejected():
    with pytest.raises(ValueError, match="长度必须相同"):
        pad_batch([([1, 2], [1])])


def test_invalid_messages_are_rejected():
    with pytest.raises(ValueError, match="不能为空"):
        encode_messages([])
    with pytest.raises(ValueError, match="不支持的 role"):
        encode_messages([{"role": "robot", "content": "hello"}])
