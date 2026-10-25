import pytest

from reprokit.output import InvalidToolResponse, parse_tool_response


def test_parse_tool_response_reads_answer() -> None:
    assert parse_tool_response('{"answer": "已关闭"}') == "已关闭"


@pytest.mark.parametrize("text", ["not-json", "{}", '{"answer": 7}'])
def test_parse_tool_response_rejects_invalid_json_or_shape(text: str) -> None:
    with pytest.raises(InvalidToolResponse):
        parse_tool_response(text)
