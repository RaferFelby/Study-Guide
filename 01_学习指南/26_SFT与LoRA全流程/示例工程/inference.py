"""读取本工程可信生成的Base和适配器；无需重新训练或安装框架。"""

import argparse
from pathlib import Path

import torch

from checkpoint import load_adapter, state_digest
from data import EOS_ID, TOKENS, encode
from model import TinyLM, merge_lora


@torch.inference_mode()
def predict(base_path, adapter_path, prompt, merged=False):
    state = torch.load(base_path, map_location="cpu", weights_only=True)
    if state["vocabulary"] != TOKENS:
        raise ValueError("Base词表与本工程不一致")
    base = TinyLM(len(TOKENS))
    base.load_state_dict(state["weights"])
    if state_digest(base) != state["base_digest"]:
        raise ValueError("Base权重摘要不一致")
    model = load_adapter(adapter_path, base, state["base_digest"]).eval()
    if merged:
        model = merge_lora(model)
    tokens = encode(prompt.split())
    if len(tokens) != 6:
        raise ValueError("本例提示需为6个固定词表token")
    inputs = torch.tensor([tokens])
    answer = []
    for _ in range(4):
        next_id = model(inputs)[0, -1].argmax().item()
        if next_id == EOS_ID:
            break
        answer.append(TOKENS[next_id])
        inputs = torch.cat([inputs, torch.tensor([[next_id]])], dim=1)
    return " ".join(answer)


def main():
    parser = argparse.ArgumentParser(description="本地微型LoRA推理")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--prompt", default="route red item 70 answer :")
    parser.add_argument("--merged", action="store_true")
    args = parser.parse_args()
    torch.set_num_threads(2)
    print(predict(args.base, args.adapter, args.prompt, args.merged))


if __name__ == "__main__":
    main()
