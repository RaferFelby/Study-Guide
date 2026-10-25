import itertools
import unittest

import torch
from app.batching import collate_integer_sequences
from torch.utils.data import DataLoader


class SequenceBatchTests(unittest.TestCase):
    def test_padding_preserves_real_zero_and_empty_sequence(self):
        values, lengths, mask = collate_integer_sequences([[4, 0], [], [7]])
        self.assertEqual(values.tolist(), [[4, 0], [0, 0], [7, 0]])
        self.assertEqual(lengths.tolist(), [2, 0, 1])
        self.assertEqual(mask.tolist(), [[True, True], [False, False], [True, False]])
        self.assertEqual(values.dtype, torch.long)
        self.assertEqual(lengths.dtype, torch.long)
        self.assertEqual(mask.dtype, torch.bool)

    def test_all_empty_sequences_preserve_batch_dimension(self):
        values, lengths, mask = collate_integer_sequences([[], []])
        self.assertEqual(tuple(values.shape), (2, 0))
        self.assertEqual(tuple(mask.shape), (2, 0))
        self.assertEqual(lengths.tolist(), [0, 0])

    def test_small_batches_reconstruct_every_original_sequence(self):
        candidates = [[], [0], [1, 0], [-1, 2, 3]]
        for sequences in itertools.product(candidates, repeat=3):
            batch = list(sequences)
            original = [sequence.copy() for sequence in batch]
            values, lengths, mask = collate_integer_sequences(batch)
            for row, sequence in enumerate(batch):
                self.assertEqual(values[row][mask[row]].tolist(), sequence)
                self.assertEqual(mask[row].sum().item(), lengths[row].item())
                self.assertTrue((values[row][~mask[row]] == 0).all().item())
            self.assertEqual(batch, original)

    def test_dataloader_keeps_last_short_batch(self):
        loader = DataLoader(
            [[4, 0], [], [7]],
            batch_size=2,
            collate_fn=collate_integer_sequences,
            num_workers=0,
        )
        first, last = list(loader)
        self.assertEqual(first[1].tolist(), [2, 0])
        self.assertEqual(last[0].tolist(), [[7]])

    def test_empty_batch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            collate_integer_sequences([])

    def test_invalid_values_and_sequence_types_are_rejected(self):
        for value in [True, 1.5, "1", None, 2**63, -(2**63) - 1]:
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "64-bit"),
            ):
                collate_integer_sequences([[value]])
        with self.assertRaisesRegex(TypeError, "must be a list"):
            collate_integer_sequences([(1, 2)])

    def test_signed_integer_boundaries_are_preserved(self):
        sequence = [-(2**63), 2**63 - 1]
        values, _, mask = collate_integer_sequences([sequence])
        self.assertEqual(values[0][mask[0]].tolist(), sequence)


if __name__ == "__main__":
    unittest.main()
