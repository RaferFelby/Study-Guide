"""单层微型GRU语言模型；所有调用token都由模型生成。"""

import torch
from torch import nn

from data import EOS_ID, PAD_ID, TOKENS, encode


class TinyToolModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(len(TOKENS), 32, padding_idx=PAD_ID)
        self.recurrent = nn.GRU(32, 48, batch_first=True)
        self.output = nn.Linear(48, len(TOKENS))

    def forward(self, inputs):
        states, _ = self.recurrent(self.embedding(inputs))
        return self.output(states)


@torch.inference_mode()
def generate(model, prompt, maximum_tokens=8):
    if (
        type(maximum_tokens) is not int
        or not 1 <= maximum_tokens <= 8
        or not prompt
        or len(prompt) > 16
    ):
        raise ValueError("生成次数或输入长度不合法")
    model.eval()
    device = next(model.parameters()).device
    inputs = torch.tensor([encode(prompt)], device=device)
    tokens = []
    for _ in range(maximum_tokens):
        token_id = model(inputs)[0, -1].argmax().item()
        tokens.append(TOKENS[token_id])
        if token_id == EOS_ID:
            break
        inputs = torch.cat([inputs, torch.tensor([[token_id]], device=device)], dim=1)
    return tokens
