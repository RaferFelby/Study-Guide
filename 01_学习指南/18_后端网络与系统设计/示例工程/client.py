import json
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener


def request(base_url, method, path, body=None, token="demo-alice"):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    message = Request(base_url + path, data=data, headers=headers, method=method)
    opener = build_opener(ProxyHandler({}))
    try:
        response = opener.open(message, timeout=3)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def main():
    base_url = "http://127.0.0.1:8765"
    for method, path, body in [
        ("GET", "/health", None),
        ("POST", "/query", {"question": "refund"}),
        ("POST", "/query", {"question": "refund"}),
        ("POST", "/jobs", {"question": "support", "request_key": "lesson-job-1"}),
    ]:
        print(request(base_url, method, path, body))


if __name__ == "__main__":
    main()
