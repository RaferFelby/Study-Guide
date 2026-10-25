import json


def parse_model_output(text, accept_json_fence=False):
    if accept_json_fence and text.startswith("```json\n") and text.endswith("\n```"):
        text = text[len("```json\n") : -len("\n```")]
    output = json.loads(text)
    if not isinstance(output, dict) or set(output) != {"status", "days"}:
        raise ValueError("回答须含status/days且无额外字段")
    if (
        output["status"] != "answered"
        or type(output["days"]) is not int
        or output["days"] < 0
    ):
        raise ValueError("回答字段取值不合法")
    return output
