import unittest

import torch

from algorithms import (
    clipped_surrogate,
    group_advantages,
    latent_attention_example,
    quantized_adapter_example,
    route_experts,
    train_bandit,
    uniform_quantize,
)


class AlgorithmTests(unittest.TestCase):
    def test_clipping_both_signs(self):
        result = clipped_surrogate(
            torch.tensor([1.5, 0.5, 1.5, 0.5]), torch.tensor([1.0, 1.0, -1.0, -1.0])
        )
        torch.testing.assert_close(result, torch.tensor([1.2, 0.5, -1.5, -0.8]))

    def test_clipped_branch_gradient_is_zero(self):
        ratios = torch.tensor([1.5, 0.5], requires_grad=True)
        clipped_surrogate(ratios, torch.tensor([1.0, -1.0])).sum().backward()
        torch.testing.assert_close(ratios.grad, torch.zeros(2))

    def test_group_normalization_and_constant(self):
        result = group_advantages(
            torch.tensor([[0.0, 1.0, 2.0, 3.0], [2.0, 2.0, 2.0, 2.0]])
        )
        torch.testing.assert_close(
            result[0], torch.tensor([-1.3416408, -0.4472136, 0.4472136, 1.3416408])
        )
        torch.testing.assert_close(result[1], torch.zeros(4))

    def test_ppo_bandit_updates(self):
        result = train_bandit("ppo")
        self.assertGreater(result["final_probability"], 0.8)
        self.assertEqual(len(result["history"]), 20)

    def test_grpo_bandit_updates(self):
        result = train_bandit("grpo")
        self.assertGreater(result["final_probability"], 0.8)
        self.assertEqual(result, train_bandit("grpo"))

    def test_expert_routing(self):
        output, indices, weights = route_experts(
            torch.tensor([[3.0, 1.0, 0.0]]), torch.tensor([[[1.0], [2.0], [3.0]]]), 2
        )
        self.assertEqual(indices.tolist(), [[0, 1]])
        torch.testing.assert_close(output, torch.tensor([[1.1192029]]))
        torch.testing.assert_close(weights.sum(dim=1), torch.ones(1))

    def test_top_one(self):
        output, _, _ = route_experts(
            torch.tensor([[0.0, 2.0]]), torch.tensor([[[3.0], [7.0]]]), 1
        )
        self.assertEqual(output.item(), 7)

    def test_latent_equivalence(self):
        result = latent_attention_example()
        self.assertLess(result["max_error"], 1e-12)
        self.assertEqual((result["kv_elements"], result["latent_elements"]), (12, 3))

    def test_quantization_zero_and_error_bound(self):
        _, _, zero = uniform_quantize(torch.zeros(2))
        torch.testing.assert_close(zero, torch.zeros(2))
        original = torch.tensor([-1.0, -0.2, 0.1, 0.9])
        codes, scale, restored = uniform_quantize(original)
        self.assertEqual(codes.dtype, torch.int8)
        self.assertLessEqual(
            (original - restored).abs().max().item(), scale.item() / 2 + 1e-7
        )

    def test_adapter_updates_only_low_rank_branch(self):
        result = quantized_adapter_example()
        self.assertLess(result["after"], result["before"] / 10)
        self.assertTrue(result["base_unchanged"])
        self.assertFalse(result["base_has_gradient"])

    def test_bad_shapes_and_nonfinite_inputs(self):
        calls = [
            lambda: clipped_surrogate(torch.ones(2), torch.ones(3)),
            lambda: clipped_surrogate(torch.tensor([float("inf")]), torch.ones(1)),
            lambda: group_advantages(torch.ones(2, 1)),
            lambda: group_advantages(torch.tensor([[1.0, float("nan")]])),
            lambda: route_experts(torch.ones(1, 2), torch.ones(1, 2, 1), 3),
            lambda: uniform_quantize(torch.tensor([float("nan")])),
            lambda: train_bandit("unknown"),
        ]
        for call in calls:
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()
