"""运行新单元Python教学片段；临时文件仅置于各自工程并自动清理。"""

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/Scripts/python.exe"


def check_unit(number):
    unit = next(
        path
        for path in (ROOT / "01_学习指南").iterdir()
        if path.name.startswith(f"{number:02d}_")
    )
    project = unit / "示例工程"
    count = 0
    for lesson in sorted((unit / "逐讲学习").glob("*.md")):
        blocks = re.findall(
            r"^```python\n(.*?)^```",
            lesson.read_text(encoding="utf-8"),
            flags=re.MULTILINE | re.DOTALL,
        )
        for block in blocks:
            reports = {
                26: "report-author-cpu-complete-20261011",
                33: "report-author-cpu-delivery-20261012",
                34: "report-author-cpu-20261013",
                36: "report-author-cpu-delivery-20261013",
                37: "report-author-cpu-delivery-20261014",
                38: "report-author-cpu-delivery-20261014",
            }
            author_report = reports.get(number, "report-author-cpu-complete-20261011")
            code = block.replace("report-my-cpu-01", author_report)
            if number == 35:
                code = code.replace(
                    "report-my-replay-01", "report-author-replay-delivery-20261013"
                )
                code = code.replace(
                    "report-my-local-cpu-01", "report-author-local-cpu-20261013"
                )
            if number == 36:
                code = code.replace(
                    "report-my-ddp-01", "report-author-ddp-temp-20261013"
                )
            # 教学命令默认手动启动8765/8766；作者批查使用自己创建的临时端口。
            if number == 24 and ("8765" in code or "8766" in code):
                prefix = "from contextlib import ExitStack\nfrom pathlib import Path\nimport json\nfrom demo import running_server\nfrom mock_source import create_source_server\nfrom server import create_app_server\nfrom service import PolicyService\nfrom adapter import HttpPolicySource\nwith ExitStack() as stack:\n    records = json.loads(Path('fixtures/policies-v1.json').read_text(encoding='utf-8'))\n    source_address = stack.enter_context(running_server(create_source_server(records)))\n    app_address = stack.enter_context(running_server(create_app_server(PolicyService(HttpPolicySource(source_address + '/policies')))))\n"
                code = code.replace(
                    '"http://127.0.0.1:8766/policies"', 'source_address + "/policies"'
                ).replace('"http://127.0.0.1:8765"', "app_address")
                code = (
                    prefix
                    + "\n".join("    " + line for line in code.splitlines())
                    + "\n"
                )
            if number == 27 and "8770" in code:
                code = code.replace('"http://127.0.0.1:8770"', "address")
                prefix = "from demo import running_server\nfrom server import create_server\nwith running_server(create_server()) as address:\n"
                code = (
                    prefix
                    + "\n".join("    " + line for line in code.splitlines())
                    + "\n"
                )
            with tempfile.TemporaryDirectory(
                prefix="author-block-", dir=project
            ) as owned:
                code = code.replace(
                    '"lesson-backup-01"', repr(str(Path(owned) / "lesson-backup-01"))
                )
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".py",
                    prefix="author-example-",
                    dir=project,
                    encoding="utf-8",
                    delete=False,
                ) as script:
                    script.write(code)
                    path = Path(script.name)
                try:
                    result = subprocess.run(
                        [str(PYTHON), str(path)],
                        cwd=project,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=60,
                        check=False,
                    )
                    if result.returncode:
                        raise RuntimeError(
                            f"{lesson.name}: {result.stdout}\n{result.stderr}"
                        )
                    count += 1
                finally:
                    path.unlink()
    print(f"单元{number:02d}：{count}个Python片段实际运行通过")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("units", nargs="+", type=int)
    args = parser.parse_args()
    for number in args.units:
        check_unit(number)


if __name__ == "__main__":
    main()
