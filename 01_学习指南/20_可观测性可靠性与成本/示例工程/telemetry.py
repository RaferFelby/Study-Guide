"""串行离线trace教学实现；没有接入遥测SDK或上传服务。"""

import json
import math
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

ALLOWED_ATTRIBUTES = {
    "model",
    "tool",
    "cache_hit",
    "input_tokens",
    "output_tokens",
    "cost_units",
    "status",
    "error_code",
    "variant",
}


def validate_attributes(attributes):
    if set(attributes) - ALLOWED_ATTRIBUTES:
        raise ValueError("遥测属性不在白名单，禁止记录原始正文/凭证")
    if any(
        not isinstance(value, (str, int, float, bool, type(None)))
        for value in attributes.values()
    ):
        raise ValueError("遥测属性只接收简单标量，不接收任意嵌套正文")
    json.dumps(attributes, allow_nan=False)


class TraceRecorder:
    def __init__(self, clock=time.perf_counter, timing_kind="measured"):
        self.clock = clock
        self.timing_kind = timing_kind
        self.events = []
        self.active_spans = []
        self.trace_id = None

    @contextmanager
    def span(self, name: str, attributes=None):
        attributes = dict(attributes or {})
        validate_attributes(attributes)
        is_root = not self.active_spans
        if is_root:
            self.trace_id = uuid4().hex
        event = {
            "trace_id": self.trace_id,
            "span_id": uuid4().hex,
            "parent_span_id": self.active_spans[-1]["span_id"]
            if self.active_spans
            else None,
            "name": name,
            "timing_kind": self.timing_kind,
            "attributes": attributes,
            "status": "ok",
            "error_type": None,
        }
        started = self.clock()
        self.active_spans.append(event)
        try:
            yield event
        except BaseException as error:
            event["status"] = "error"
            event["error_type"] = type(error).__name__
            raise
        finally:
            self.active_spans.pop()
            if is_root:
                self.trace_id = None
            elapsed = self.clock() - started
            if not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("时钟持续时间必须非负有限")
            event["duration_ms"] = round(elapsed * 1000, 6)
            validate_attributes(event["attributes"])
            self.events.append(event)

    def write_jsonl(self, path: Path):
        # x模式拒绝覆盖旧记录；每行一个JSON对象，适合逐行检查。
        with path.open("x", encoding="utf-8") as stream:
            for event in self.events:
                stream.write(
                    json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n"
                )


class SimulatedClock:
    def __init__(self):
        self.seconds = 0.0

    def __call__(self):
        return self.seconds

    def advance(self, seconds: float):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("模拟时间增量必须非负有限")
        self.seconds += seconds
