"""用于教材勘误的最小标准库反例，不依赖示例工程包。"""

from contextlib import contextmanager

import pytest


def test_generator_cleanup_after_yield_is_skipped_on_error():
    actions = []

    @contextmanager
    def after_yield():
        yield
        actions.append("after")

    @contextmanager
    def with_finally():
        try:
            yield
        finally:
            actions.append("finally")

    with pytest.raises(ValueError), after_yield():
        raise ValueError("块内异常")
    assert actions == []
    with pytest.raises(ValueError), with_finally():
        raise ValueError("块内异常")
    assert actions == ["finally"]


def test_raising_in_except_preserves_implicit_exception_context():
    original = ValueError("底层原因")
    with pytest.raises(RuntimeError) as captured:
        try:
            raise original
        except ValueError:
            raise RuntimeError("上层说明")
    assert captured.value.__context__ is original
    assert captured.value.__cause__ is None


def test_tuple_hashability_depends_on_its_elements():
    mapping = {(1, "a"): "可用"}
    assert mapping[(1, "a")] == "可用"
    with pytest.raises(TypeError):
        hash((1, [2]))
