import argparse
import json

import torch

from algorithms import (
    clipped_surrogate,
    group_advantages,
    latent_attention_example,
    quantized_adapter_example,
    route_experts,
    train_bandit,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "experiment",
        choices=["clip", "group", "ppo", "grpo", "moe", "latent", "adapter"],
    )
    args = parser.parse_args()
    torch.set_num_threads(1)
    if args.experiment == "clip":
        result = clipped_surrogate(
            torch.tensor([1.5, 0.5, 1.5, 0.5]), torch.tensor([1.0, 1.0, -1.0, -1.0])
        ).tolist()
    elif args.experiment == "group":
        result = group_advantages(
            torch.tensor([[0.0, 1.0, 2.0, 3.0], [1.0, 1.0, 1.0, 1.0]])
        ).tolist()
    elif args.experiment in {"ppo", "grpo"}:
        result = train_bandit(args.experiment)
    elif args.experiment == "moe":
        scores = torch.tensor([[3.0, 1.0, 0.0], [0.0, 1.0, 3.0]])
        experts = torch.tensor([[[1.0], [2.0], [3.0]], [[1.0], [2.0], [3.0]]])
        output, indices, weights = route_experts(scores, experts, 2)
        result = {
            "output": output.tolist(),
            "indices": indices.tolist(),
            "weights": weights.tolist(),
        }
    elif args.experiment == "latent":
        result = latent_attention_example()
    else:
        result = quantized_adapter_example()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
