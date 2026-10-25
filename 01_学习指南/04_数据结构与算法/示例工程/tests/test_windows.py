import itertools
import unittest

from app.window_practice import (
    busiest_window,
    deduplicate_sorted,
    min_positive_subarray_length,
)


class WindowPracticeTests(unittest.TestCase):
    def test_deduplication_keeps_valid_prefix(self):
        for values, expected in (
            ([], []),
            ([2, 2, 2], [2]),
            ([-1, -1, 0, 2, 2], [-1, 0, 2]),
        ):
            with self.subTest(values=values):
                original_length = len(values)
                count = deduplicate_sorted(values)
                self.assertEqual(values[:count], expected)
                self.assertEqual(len(values), original_length)

    def test_deduplication_validates_before_mutating(self):
        for values in ([1, 1, 3, 2], [1, True], [1, 1.5]):
            with self.subTest(values=values):
                before = values.copy()
                with self.assertRaises(ValueError):
                    deduplicate_sorted(values)
                self.assertEqual(values, before)

    def test_min_length_examples_and_boundaries(self):
        self.assertEqual(min_positive_subarray_length([2, 3, 1, 2, 4, 3], 7), 2)
        self.assertEqual(min_positive_subarray_length([], 7), 0)
        self.assertEqual(min_positive_subarray_length([1, 2], 7), 0)
        self.assertEqual(min_positive_subarray_length([9], 7), 1)

    def test_min_length_rejects_invalid_contract(self):
        for values, target in (
            ([1, -1, 5], 5),
            ([0, 1], 1),
            ([True], 1),
            ([1.5], 1),
            ([1], 0),
            ([1], True),
        ):
            with (
                self.subTest(values=values, target=target),
                self.assertRaises(ValueError),
            ):
                min_positive_subarray_length(values, target)

    def test_min_length_matches_small_brute_force(self):
        for length in range(6):
            for values in itertools.product((1, 2, 3), repeat=length):
                for target in range(1, 11):
                    best = length + 1
                    for start in range(length):
                        for stop in range(start + 1, length + 1):
                            if sum(values[start:stop]) >= target:
                                best = min(best, stop - start)
                    expected = 0 if best > length else best
                    self.assertEqual(
                        min_positive_subarray_length(list(values), target), expected
                    )

    def test_log_half_open_time_boundary_and_duplicates(self):
        self.assertEqual(busiest_window([0, 60]), (0, 1))
        self.assertEqual(busiest_window([0, 59, 60, 60, 119]), (1, 4))
        self.assertEqual(busiest_window([5, 5, 5]), (0, 3))

    def test_log_empty_single_and_cross_day(self):
        self.assertIsNone(busiest_window([]))
        self.assertEqual(busiest_window([0]), (0, 1))
        self.assertEqual(busiest_window([86390, 86410, 86420]), (0, 3))

    def test_log_rejects_unsorted_or_invalid_times(self):
        for times, window in (
            ([1, 0], 60),
            ([-1], 60),
            ([True], 60),
            ([1.5], 60),
            ([1], 0),
            ([1], True),
        ):
            with (
                self.subTest(times=times, window=window),
                self.assertRaises(ValueError),
            ):
                busiest_window(times, window)

    def test_log_matches_brute_force_with_first_tie(self):
        for length in range(6):
            for times in itertools.combinations_with_replacement(
                (0, 30, 60, 90), length
            ):
                best = None
                best_count = 0
                for end_time in times:
                    indices = [
                        i
                        for i, value in enumerate(times)
                        if end_time - 60 < value <= end_time
                    ]
                    if len(indices) > best_count:
                        best = (indices[0], indices[-1] + 1)
                        best_count = len(indices)
                self.assertEqual(busiest_window(list(times)), best)


if __name__ == "__main__":
    unittest.main()
