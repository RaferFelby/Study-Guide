"""两个本机CPU进程的真实Gloo/DDP一步，比较同一全批次参考。"""

import argparse
import json
import tempfile
from datetime import timedelta
from pathlib import Path

import torch
from torch import distributed, multiprocessing, nn
from torch.nn.parallel import DistributedDataParallel


def make_model():
    model = nn.Linear(2, 1, bias=False)
    with torch.no_grad():
        model.weight.copy_(torch.tensor([[0.5, -0.25]]))
    return model


def make_data():
    return torch.tensor([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]), torch.tensor(
        [[1.0], [2.0], [3.0], [4.0]]
    )


def worker(rank, rendezvous, output_dir):
    torch.set_num_threads(1)
    distributed.init_process_group(
        "gloo",
        init_method=rendezvous,
        rank=rank,
        world_size=2,
        timeout=timedelta(seconds=30),
    )
    try:
        model = DistributedDataParallel(make_model())
        inputs, targets = make_data()
        selected = slice(rank * 2, (rank + 1) * 2)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        loss = (model(inputs[selected]) - targets[selected]).square().mean()
        loss.backward()
        optimizer.step()
        torch.save(
            {
                "rank": rank,
                "world_size": 2,
                "completed_steps": 1,
                "weights": model.module.state_dict(),
                "purpose": "replicated_DDP_weights_not_sharded_checkpoint_or_exact_resume",
            },
            output_dir / f"rank-{rank}.pt",
        )
        distributed.barrier()
    finally:
        distributed.destroy_process_group()


def run(output_dir):
    if not distributed.is_available() or not distributed.is_gloo_available():
        raise ValueError("需要当前PyTorch可用Gloo后端")
    output_dir.mkdir(parents=True, exist_ok=False)
    # Windows原生FileStore对路径支持有限；通信临时文件置于系统临时目录。
    with tempfile.TemporaryDirectory(prefix="unit36-rendezvous-") as owned:
        rendezvous = (Path(owned) / "init-file").resolve().as_uri()
        multiprocessing.spawn(
            worker, args=(rendezvous, output_dir), nprocs=2, join=True
        )
    inputs, targets = make_data()
    reference = make_model()
    optimizer = torch.optim.SGD(reference.parameters(), lr=0.1)
    optimizer.zero_grad(set_to_none=True)
    loss = (reference(inputs) - targets).square().mean()
    loss.backward()
    optimizer.step()
    rank_weights = [
        torch.load(output_dir / f"rank-{rank}.pt", weights_only=True)["weights"][
            "weight"
        ]
        for rank in range(2)
    ]
    difference = max(
        float((weights - reference.weight.detach()).abs().max())
        for weights in rank_weights
    )
    if difference > 1e-6 or not torch.equal(rank_weights[0], rank_weights[1]):
        raise AssertionError("DDP结果与全批次参考不一致")
    report = {
        "scope": "actual_two_CPU_processes_Gloo_DDP_not_two_GPUs",
        "world_size": 2,
        "local_samples": 2,
        "global_samples": 4,
        "gradient_reduction": "mean_of_equal_local_batch_mean_losses",
        "reference_weights": reference.weight.detach().tolist(),
        "max_abs_difference": difference,
        "checkpoint_scope": "two_replicated_rank_weights_not_FSDP_shards_or_exact_resume",
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
