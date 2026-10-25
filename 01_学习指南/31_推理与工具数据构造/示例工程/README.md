---
title: 推理与工具数据示例工程代码导航
tags: [learning, dataset, tool-trace]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 推理与工具数据示例工程代码导航

> [!nav] 页面导航
> [[01_学习指南/31_推理与工具数据构造/00 推理与工具数据构造学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/31_推理与工具数据构造/逐讲学习/01 把问题计划工具轨迹与答案放进一条样本|从第一讲开始：把问题计划工具轨迹与答案放进一条样本]]

## 先运行

VS Code打开本目录，选择根共享解释器，PowerShell运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe pipeline.py --output-dir report-my-01
```

新目录拒绝覆盖。标准库运行，无模型/API/下载/真实资料/新依赖。候选55→自动通过50→去重48→train28/dev10/test10；8条抽检待办，无真人签署、训练或学习曲线。

## 代码导航

- [data.py](./data.py)：合成来源/候选/坏例、文本规范化、内容指纹及保留不同依据的去重。
- [validation.py](./validation.py)：字段、来源/版本、固定工具重放、调用关联、已知问题模板和答案检查。
- [splitting.py](./splitting.py)：来源/题族/指纹传递分组、固定seed切分、四类跨集合泄漏检查。
- [formatting.py](./formatting.py)：五消息模板、UTF-8字节输入和assistant监督标签、8条待真人抽检表。
- [pipeline.py](./pipeline.py)：候选数据包、摘要与未完成状态，不覆盖旧目录。
- [test_dataset.py](./tests/test_dataset.py)：错误、去重保据、传递分组、泄漏、标签、抽检和导出测试。
- [conftest.py](./tests/conftest.py)：仅本工程测试的源码目录。
- [requirements.txt](./requirements.txt)：标准库，测试/格式工具沿用共享环境。

## 结果文件

新目录包含raw.jsonl、candidates.jsonl、sources.json、train/dev/test.jsonl、report.json、review_sheet.json，共8个文件。完整候选保留逐条来源/计划/轨迹；三份messages仍标candidate_only_pending_human_review。原始错误与重复记录不删除，报告保存拒绝原因与removed/kept映射。

## 检查命令

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

作者28项测试通过；首条教学模板输入348字节/监督132字节，两段assistant监督。不是LLM token/EOS/真实模型格式；超长拒绝不静默截断。单元26训练器不能直接读取本多轮工具数据。

## 边界与教材

只校验固定加法和两种问题模板，plan_summary语义未自动验证；不是通用事实裁判。内容指纹不保证语义近重复全检，分组算法适合小规模教学，不宣称大数据性能。usage_policy是合成教学范围，不证明外部许可。人工表pending不代表已抽检；数量充分性需实际学习曲线。

[[01_学习指南/31_推理与工具数据构造/00 推理与工具数据构造学习地图|六讲正文]] · [[90_参考与维护/单元验证/31 推理与工具数据构造验证记录|作者结果与待办]]。
