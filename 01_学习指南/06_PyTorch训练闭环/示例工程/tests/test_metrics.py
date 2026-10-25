import unittest

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from app.diagnostics import describe_tensor, weighted_mean_loss
from app.training import check_batch, evaluate, train_one_epoch


class MetricTests(unittest.TestCase):
    def test_weighted_mean_matches_individual_observations(self):
        losses = [1.0, 3.0, 9.0]
        expected = sum(losses) / len(losses)
        self.assertAlmostEqual(weighted_mean_loss([(2.0, 2), (9.0, 1)]), expected)
        self.assertAlmostEqual(
            weighted_mean_loss([(loss, 1) for loss in losses]), expected
        )
        self.assertNotAlmostEqual((2.0 + 9.0) / 2, expected)

    def test_weighted_mean_rejects_empty_nonfinite_and_bad_counts(self):
        invalid = [[], [(float("nan"), 1)], [(float("inf"), 1)]]
        for count in (0, -1, 1.5, True):
            invalid.append([(1.0, count)])
        invalid.append([(1e308, 2)])
        for records in invalid:
            with self.subTest(records=records), self.assertRaises(ValueError):
                weighted_mean_loss(records)

    def test_description_reports_nonfinite_values_without_mutating_input(self):
        values = torch.tensor([[1.0, float("nan")], [-2.0, float("inf")]])
        original = values.clone()
        summary = describe_tensor(values)
        self.assertEqual(summary["shape"], [2, 2])
        self.assertEqual(summary["dtype"], "torch.float32")
        self.assertEqual(summary["nan_count"], 1)
        self.assertEqual(summary["inf_count"], 1)
        self.assertEqual(summary["finite_min"], -2.0)
        self.assertEqual(summary["finite_max"], 1.0)
        torch.testing.assert_close(values, original, equal_nan=True)

    def test_description_handles_empty_and_all_nonfinite_values(self):
        for values in (torch.empty(0, 1), torch.tensor([float("nan"), float("inf")])):
            with self.subTest(shape=values.shape):
                summary = describe_tensor(values)
                self.assertIsNone(summary["finite_min"])
                self.assertIsNone(summary["finite_max"])
        with self.assertRaisesRegex(ValueError, "complex"):
            describe_tensor(torch.tensor([1j]))

    def test_evaluation_is_independent_of_batch_partition_and_uses_element_mean(self):
        features = torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        targets = torch.zeros_like(features)
        dataset = TensorDataset(features, targets)
        expected = 91.0 / 6
        for batch_size in (1, 2, 3):
            loader = DataLoader(dataset, batch_size=batch_size)
            result = evaluate(nn.Identity(), loader, torch.device("cpu"))
            self.assertAlmostEqual(result["loss"], expected)

    def test_training_and_validation_agree_when_weights_are_not_updated(self):
        model = nn.Linear(2, 2, bias=False)
        with torch.no_grad():
            model.weight.copy_(torch.eye(2))
        features = torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        loader = DataLoader(
            TensorDataset(features, torch.zeros_like(features)), batch_size=2
        )
        # lr=0 仅用于此隔离对照，排除参数更新造成的测量差异。
        optimizer = torch.optim.SGD(model.parameters(), lr=0.0)
        training = train_one_epoch(
            model,
            loader,
            optimizer,
            torch.device("cpu"),
            torch.amp.GradScaler("cpu", enabled=False),
            clip_norm=None,
        )
        validation = evaluate(model, loader, torch.device("cpu"))
        self.assertAlmostEqual(training["loss"], validation["loss"], places=5)

    def test_validation_does_not_update_parameters_or_record_gradients(self):
        model = nn.Linear(1, 1)
        original = [parameter.detach().clone() for parameter in model.parameters()]
        observed_gradient_modes = []

        def record_gradient_mode(module, inputs, output):
            observed_gradient_modes.append(torch.is_grad_enabled())

        handle = model.register_forward_hook(record_gradient_mode)
        values = torch.ones(3, 1)
        evaluate(model, DataLoader(TensorDataset(values, values)), torch.device("cpu"))
        handle.remove()
        for parameter, previous in zip(model.parameters(), original):
            torch.testing.assert_close(parameter, previous)
            self.assertIsNone(parameter.grad)
        self.assertEqual(observed_gradient_modes, [False, False, False])
        self.assertFalse(model.training)

    def test_training_contract_rejects_empty_batches_and_empty_features(self):
        for features, targets in (
            (torch.empty(0, 1), torch.empty(0, 1)),
            (torch.empty(2, 0), torch.ones(2, 1)),
            (torch.ones(2, 1), torch.empty(2, 0)),
        ):
            with (
                self.subTest(shape=features.shape),
                self.assertRaisesRegex(ValueError, "cannot be empty"),
            ):
                check_batch(features, targets)

    def test_shape_mismatch_is_rejected_before_broadcasting(self):
        model = nn.Linear(1, 2)
        values = torch.ones(2, 1)
        loader = DataLoader(TensorDataset(values, values), batch_size=2)
        with self.assertRaisesRegex(ValueError, "shapes differ"):
            evaluate(model, loader, torch.device("cpu"))
        with self.assertRaisesRegex(ValueError, "shapes differ"):
            train_one_epoch(
                model,
                loader,
                torch.optim.SGD(model.parameters(), lr=0.1),
                torch.device("cpu"),
                torch.amp.GradScaler("cpu", enabled=False),
            )

    def test_injected_nan_identifies_batch_without_updating_model(self):
        model = nn.Linear(1, 1)
        original = model.weight.detach().clone()
        values = torch.ones(2, 1)
        loader = DataLoader(TensorDataset(values, values), batch_size=2)
        with self.assertRaisesRegex(ValueError, "invalid training batch 0.*NaN"):
            train_one_epoch(
                model,
                loader,
                torch.optim.SGD(model.parameters(), lr=0.1),
                torch.device("cpu"),
                torch.amp.GradScaler("cpu", enabled=False),
                inject_nan=True,
            )
        torch.testing.assert_close(model.weight, original)


if __name__ == "__main__":
    unittest.main()
