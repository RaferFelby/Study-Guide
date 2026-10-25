import json
from copy import deepcopy
from decimal import Decimal

from costs import model_cost
from telemetry import SimulatedClock, TraceRecorder

VARIANTS = {"baseline", "cached", "routed", "cache_routed", "bad_crop"}


def mock_model(question, documents):
    if "VIP" in question:
        return {"status": "refused", "days": None}
    if len({doc["days"] for doc in documents}) > 1:
        return {"status": "needs_review", "days": None}
    return {"status": "answered", "days": documents[0]["days"]}


class Pipeline:
    def __init__(self, variant: str):
        if variant not in VARIANTS:
            raise ValueError("未知实验版本")
        self.variant = variant
        self.clock = SimulatedClock()
        self.recorder = TraceRecorder(self.clock, timing_kind="simulated")
        self.cache = {}

    def run(self, input_data: dict):
        data = deepcopy(input_data)
        uses_cache = self.variant in {"cached", "cache_routed"}
        key = (data["owner"], data["knowledge_version"], data["question"])
        with self.recorder.span("task", {"variant": self.variant}) as root:
            cost = Decimal(0)
            tokens_in = tokens_out = 0
            with self.recorder.span(
                "cache_lookup", {"cache_hit": uses_cache and key in self.cache}
            ):
                self.clock.advance(0.005)
            if uses_cache and key in self.cache:
                output = deepcopy(self.cache[key])
                cache_hit = True
            else:
                cache_hit = False
                try:
                    with self.recorder.span("tool", {"tool": "search_policy"}):
                        self.clock.advance(0.1)
                        if data["timeout"]:
                            raise TimeoutError("合成上游超时")
                        documents = data["documents"]
                except TimeoutError:
                    output = {
                        "status": "failed",
                        "days": None,
                        "error_code": "upstream_timeout",
                    }
                    cost += Decimal("0.01")
                else:
                    cost += Decimal("0.01")
                    question = data["question"]
                    if self.variant == "bad_crop":
                        question = question.replace(" VIP", "")
                        documents = documents[:1]
                    uses_route = self.variant in {"routed", "cache_routed"}
                    model = (
                        "small-mock"
                        if uses_route and len(documents) == 1 and "VIP" not in question
                        else "large-mock"
                    )
                    with self.recorder.span("model", {"model": model}) as span:
                        output = mock_model(question, documents)
                        # 假供应商的usage夹具：UTF-8字节数模拟token，非真实tokenizer。
                        tokens_in = len(
                            json.dumps(
                                [question, documents], ensure_ascii=False
                            ).encode("utf-8")
                        )
                        tokens_out = len(json.dumps(output).encode("utf-8"))
                        amount = model_cost(model, tokens_in, tokens_out)
                        cost += amount
                        span["attributes"].update(
                            {
                                "input_tokens": tokens_in,
                                "output_tokens": tokens_out,
                                "cost_units": str(amount),
                            }
                        )
                        self.clock.advance(0.05 if model == "small-mock" else 0.2)
                    if uses_cache:
                        if len(self.cache) >= 32:
                            self.cache.pop(next(iter(self.cache)))
                        self.cache[key] = deepcopy(output)
            root["attributes"].update(
                {
                    "status": output["status"],
                    "cache_hit": cache_hit,
                    "input_tokens": tokens_in,
                    "output_tokens": tokens_out,
                    "cost_units": str(cost),
                }
            )
            if output["status"] == "failed":
                root["attributes"]["error_code"] = output["error_code"]
        return {
            "output": output,
            "trace_id": root["trace_id"],
            "duration_ms": root["duration_ms"],
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "cost_units": str(cost),
            "cache_hit": cache_hit,
        }
