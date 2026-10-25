import importlib.util
import tempfile
import unittest
from pathlib import Path

TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None

if TORCH_AVAILABLE:
    import torch
    from app.data import build_loaders, make_dataset
    from app.model import TinyRegressor, parameter_summary
    from app.training import (
        EarlyStopping,
        check_batch,
        evaluate,
        load_checkpoint,
        save_checkpoint,
        train_one_epoch,
    )
    from torch.utils.data import DataLoader, TensorDataset


@unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed")
class TrainingComponentTests(unittest.TestCase):
    def test_dataset_split_and_model_shape(self):
        dataset = make_dataset(size=20, seed=3)
        train_loader, valid_loader = build_loaders(dataset, batch_size=4, seed=3)
        small_train_loader, same_valid_loader = build_loaders(
            dataset,
            batch_size=4,
            seed=3,
            max_train_samples=5,
        )
        features, targets = next(iter(train_loader))
        model = TinyRegressor(hidden_size=8)
        predictions = model(features)
        self.assertEqual(predictions.shape, targets.shape)
        self.assertEqual(len(train_loader.dataset) + len(valid_loader.dataset), 20)
        self.assertEqual(len(small_train_loader.dataset), 5)
        self.assertEqual(len(same_valid_loader.dataset), len(valid_loader.dataset))
        self.assertEqual(parameter_summary(model)["trainable"], 25)

    def test_batch_check_rejects_nan(self):
        features = torch.tensor([[float("nan")]])
        targets = torch.tensor([[1.0]])
        with self.assertRaisesRegex(ValueError, "NaN"):
            check_batch(features, targets)

    def test_early_stopping_patience(self):
        stopper = EarlyStopping(patience=2)
        self.assertFalse(stopper.update(1.0))
        self.assertFalse(stopper.update(1.1))
        self.assertTrue(stopper.update(1.2))
        for metric in (float("nan"), float("inf")):
            with (
                self.subTest(metric=metric),
                self.assertRaisesRegex(
                    ValueError,
                    "metric must be finite",
                ),
            ):
                stopper.update(metric)

    def test_empty_loaders_fail_with_clear_errors(self):
        empty_dataset = TensorDataset(torch.empty((0, 1)), torch.empty((0, 1)))
        empty_loader = DataLoader(empty_dataset, batch_size=4)
        model = TinyRegressor()
        optimizer = torch.optim.AdamW(model.parameters())
        scaler = torch.amp.GradScaler("cpu", enabled=False)

        with self.assertRaisesRegex(ValueError, "training loader cannot be empty"):
            train_one_epoch(
                model,
                empty_loader,
                optimizer,
                torch.device("cpu"),
                scaler,
            )
        with self.assertRaisesRegex(ValueError, "validation loader cannot be empty"):
            evaluate(model, empty_loader, torch.device("cpu"))

    def test_checkpoint_round_trip(self):
        model = TinyRegressor()
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2)
        stopper = EarlyStopping()
        scaler = torch.amp.GradScaler("cpu", enabled=False)
        model(torch.ones((1, 1))).sum().backward()
        optimizer.step()
        scheduler.step()
        stopper.update(0.5)
        training_config = {
            "seed": 7,
            "batch_size": 4,
            "learning_rate": 0.01,
            "clip_norm": 1.0,
            "patience": 5,
            "amp": False,
            "overfit_small": False,
            "inject_nan": False,
            "device": "cpu",
        }
        torch.manual_seed(17)
        with tempfile.TemporaryDirectory(
            dir=Path(__file__).resolve().parents[1]
        ) as directory:
            path = Path(directory) / "checkpoint.pt"
            save_checkpoint(
                path,
                model,
                optimizer,
                scheduler,
                3,
                [],
                stopper,
                scaler,
                training_config,
            )
            expected_next_random = torch.rand(3)
            torch.rand(3)
            restored = TinyRegressor()
            restored_optimizer = torch.optim.AdamW(restored.parameters(), lr=0.01)
            restored_scheduler = torch.optim.lr_scheduler.StepLR(
                restored_optimizer,
                step_size=2,
            )
            restored_stopper = EarlyStopping()
            restored_scaler = torch.amp.GradScaler("cpu", enabled=False)
            checkpoint = load_checkpoint(
                path,
                restored,
                restored_optimizer,
                restored_scheduler,
                restored_stopper,
                restored_scaler,
                torch.device("cpu"),
                training_config,
            )
            self.assertEqual(checkpoint["epoch"], 3)
            self.assertEqual(restored_stopper.best, 0.5)
            self.assertEqual(restored_scheduler.last_epoch, scheduler.last_epoch)
            for saved_parameter, restored_parameter in zip(
                model.parameters(),
                restored.parameters(),
            ):
                torch.testing.assert_close(saved_parameter, restored_parameter)
            torch.testing.assert_close(torch.rand(3), expected_next_random)


def test_epoch_boundary_resume_matches_uninterrupted_training(tmp_path, monkeypatch):
    from argparse import Namespace

    from train import run

    # 此项明确验证CPU路径；不据此声称CUDA/跨版本位级等价。
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    def settings(output, epochs, resume=None):
        return Namespace(
            seed=7,
            batch_size=16,
            learning_rate=0.01,
            clip_norm=1.0,
            patience=100,
            amp=False,
            overfit_small=False,
            inject_nan=False,
            output_dir=output,
            epochs=epochs,
            resume=resume,
        )

    full_history = run(settings(tmp_path / "full", 4))
    run(settings(tmp_path / "resumed", 2))
    resumed_history = run(
        settings(tmp_path / "resumed", 4, tmp_path / "resumed/last.pt")
    )
    full = torch.load(tmp_path / "full/last.pt", weights_only=True)
    resumed = torch.load(tmp_path / "resumed/last.pt", weights_only=True)
    assert full["epoch"] == resumed["epoch"] == 3
    for name, expected in full["model_state_dict"].items():
        torch.testing.assert_close(
            expected, resumed["model_state_dict"][name], rtol=0, atol=0
        )
    assert full["scheduler_state_dict"] == resumed["scheduler_state_dict"]
    assert full["early_stopping"] == resumed["early_stopping"]
    assert (
        full["optimizer_state_dict"]["param_groups"]
        == resumed["optimizer_state_dict"]["param_groups"]
    )
    for parameter_id, state in full["optimizer_state_dict"]["state"].items():
        for name, expected in state.items():
            torch.testing.assert_close(
                expected,
                resumed["optimizer_state_dict"]["state"][parameter_id][name],
                rtol=0,
                atol=0,
            )
    torch.testing.assert_close(
        full["torch_rng_state"], resumed["torch_rng_state"], rtol=0, atol=0
    )
    for before, after in zip(full_history, resumed_history, strict=True):
        for field in ("epoch", "train_loss", "valid_loss", "learning_rate"):
            assert before[field] == after[field]


if __name__ == "__main__":
    unittest.main()
