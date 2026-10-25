"""Embedding→单层GRU→词表投影的微型因果语言模型。"""

import torch
from torch import nn

from data import EOS_ID, PAD_ID, TOKENS, encode


class TinyLanguageModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(len(TOKENS), 24, padding_idx=PAD_ID)
        self.recurrent = nn.GRU(24, 32, batch_first=True)
        self.output = nn.Linear(32, len(TOKENS))

    def forward(self, inputs):
        features = self.embedding(inputs)
        states, _ = self.recurrent(features)
        return self.output(states)


@torch.inference_mode()
def generate(model, prompt, maximum_tokens=8):
    if type(maximum_tokens) is not int or not 1 <= maximum_tokens <= 8:
        raise ValueError("生成上限需为1～8整数")
    model.eval()
    device = next(model.parameters()).device
    inputs = torch.tensor([encode(prompt)], dtype=torch.long, device=device)
    answer = []
    for _ in range(maximum_tokens):
        token_id = model(inputs)[0, -1].argmax().item()
        answer.append(TOKENS[token_id])
        if token_id == EOS_ID:
            break
        inputs = torch.cat([inputs, torch.tensor([[token_id]], device=device)], dim=1)
    return answer
