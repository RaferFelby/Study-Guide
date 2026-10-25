import itertools
import math
import unittest
from statistics import NormalDist

from app.distributions import binomial_probability, summarize_population


class DistributionTests(unittest.TestCase):
    def test_binomial_probabilities_match_enumerated_sequences(self):
        for trials in range(5):
            for probability in (0.0, 0.2, 0.5, 1.0):
                expected = [0.0] * (trials + 1)
                for sequence in itertools.product((0, 1), repeat=trials):
                    sequence_probability = 1.0
                    for outcome in sequence:
                        sequence_probability *= (
                            probability if outcome else 1 - probability
                        )
                    expected[sum(sequence)] += sequence_probability
                actual = []
                for successes in range(trials + 1):
                    actual.append(binomial_probability(trials, successes, probability))
                    self.assertAlmostEqual(actual[-1], expected[successes])
                self.assertAlmostEqual(sum(actual), 1.0)

    def test_binomial_rejects_invalid_counts_and_probabilities(self):
        invalid = [
            (-1, 0, 0.5),
            (3, -1, 0.5),
            (3, 4, 0.5),
            (3.0, 1, 0.5),
            (True, 1, 0.5),
            (3, 1, -0.1),
            (3, 1, 1.1),
            (3, 1, math.nan),
            (3, 1, math.inf),
        ]
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                binomial_probability(*arguments)

    def test_population_statistics_match_hand_calculation(self):
        self.assertEqual(
            summarize_population([8, 8, 12, 12]),
            {"mean": 10, "variance": 4, "standard_deviation": 2},
        )
        self.assertEqual(
            summarize_population([6, 6, 14, 14]),
            {"mean": 10, "variance": 16, "standard_deviation": 4},
        )
        self.assertEqual(
            summarize_population([7]),
            {"mean": 7, "variance": 0, "standard_deviation": 0},
        )

    def test_population_variance_changes_with_scaling_not_translation(self):
        values = [1, 2, 5]
        original = summarize_population(values)
        shifted = summarize_population([value + 10 for value in values])
        scaled = summarize_population([value * 3 for value in values])
        self.assertAlmostEqual(shifted["variance"], original["variance"])
        self.assertAlmostEqual(scaled["variance"], 9 * original["variance"])
        self.assertAlmostEqual(
            scaled["standard_deviation"], 3 * original["standard_deviation"]
        )

    def test_population_rejects_missing_or_nonfinite_observations(self):
        for values in ([], [math.nan], [1, math.inf]):
            with self.assertRaises(ValueError):
                summarize_population(values)

    def test_normal_model_interval_is_symmetric_and_bounded(self):
        model = NormalDist(mu=10, sigma=2)
        self.assertAlmostEqual(model.cdf(10), 0.5)
        within_one_deviation = model.cdf(12) - model.cdf(8)
        self.assertAlmostEqual(within_one_deviation, 0.6826894921370859)
        self.assertAlmostEqual(
            model.cdf(10) - model.cdf(8), model.cdf(12) - model.cdf(10)
        )


if __name__ == "__main__":
    unittest.main()
