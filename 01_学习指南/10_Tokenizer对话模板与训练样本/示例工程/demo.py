"""运行一个无需下载模型的对话样本构造演示。"""

from chat_data import count_supervised_tokens, encode_messages, pad_batch
from tokenizer import decode_ids


def main() -> None:
    messages = [
        {"role": "user", "content": "北京天气怎么样？"},
        {"role": "assistant", "recipient": "weather", "content": "查询北京天气"},
        {"role": "tool", "content": "晴，18℃"},
        {"role": "assistant", "content": "北京晴，气温 18℃。"},
    ]
    input_ids, labels = encode_messages(messages)
    batch = pad_batch([(input_ids, labels)])

    print("对话可读形式：", decode_ids(input_ids))
    print("input token 数：", len(input_ids))
    print("有效监督 token 数：", count_supervised_tokens(labels))
    print("attention mask 长度：", len(batch["attention_mask"][0]))


if __name__ == "__main__":
    main()
