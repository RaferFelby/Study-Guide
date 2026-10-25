"""可控延迟的模拟推理后端；输出单位不是模型token。"""

import math


class GenerationCancelled(Exception):
    pass


class SyntheticBackend:
    name = "synthetic_delay_not_llm"

    def __init__(self, prefill_per_unit=0.003, decode_seconds=0.006):
        if not all(
            math.isfinite(value) and 0 <= value <= 0.2
            for value in (prefill_per_unit, decode_seconds)
        ):
            raise ValueError("模拟延迟需为0至0.2秒有限数")
        self.prefill_per_unit = prefill_per_unit
        self.decode_seconds = decode_seconds

    def generate(self, prompt, output_units, cancelled):
        if cancelled.wait(len(prompt.split()) * self.prefill_per_unit):
            raise GenerationCancelled
        for index in range(output_units):
            if cancelled.wait(self.decode_seconds):
                raise GenerationCancelled
            yield f"片段{index + 1} "
