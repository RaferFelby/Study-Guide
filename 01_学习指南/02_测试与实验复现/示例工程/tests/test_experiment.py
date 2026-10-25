import pytest

from reprokit.experiment import run


def test_same_configuration_produces_same_result() -> None:
    first = run(seed=7, data_version="demo-v1")
    second = run(seed=7, data_version="demo-v1")

    assert first == second


def test_seed_is_part_of_experiment_evidence() -> None:
    result = run(seed=7, data_version="demo-v1", rounds=2)

    assert result["config"] == {"seed": 7, "rounds": 2}
    assert result["data_version"] == "demo-v1"


def test_rounds_must_be_positive() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        run(seed=7, data_version="demo-v1", rounds=0)
