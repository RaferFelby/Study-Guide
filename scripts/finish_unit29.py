"""补全本轮教学说明和已观察到的验证结果；保留学习者勾选。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ROOT / "01_学习指南"
UNIT = GUIDES / "29_规划工作流与重新规划"


def insert_before(path, heading, text):
    original = path.read_text(encoding="utf-8")
    if heading not in original or text.strip() in original:
        raise ValueError(f"插入位置不存在或已执行：{path.name}")
    path.write_text(
        original.replace(heading, text + "\n" + heading, 1), encoding="utf-8"
    )


def main():
    lessons = sorted((UNIT / "逐讲学习").glob("*.md"))
    additions = [
        """## 第一次运行时按这五步操作

1. 在 VS Code 中选择“文件 → 打开文件夹”，打开工作区中的 `01_学习指南/29_规划工作流与重新规划/示例工程`，不要只打开一份孤立的脚本。
2. 在左侧资源管理器中点击“新建文件”，输入 `lesson_01.py`，复制上面的最小示例并保存。这里只复制教学片段，不改 `workflow.py`。
3. 打开“终端 → 新建终端”。确认终端路径结尾是本单元的 `示例工程`；若在根目录，先用 `Set-Location '01_学习指南/29_规划工作流与重新规划/示例工程'` 进入。
4. 运行上面的命令。PowerShell 中 `&` 表示执行随后指定的程序；`..` 是上一级目录，三个 `..` 回到工作区根，随后使用已有 `.venv` 的 Python。
5. 看输出而不是只看“没有报错”：应有四行，读取政策和工单的依赖为空，草稿依赖两份资料，检查依赖草稿。以后各讲的 `lesson_02.py` 等文件都放在这个工程中。

## 最小代码逐行读

`from workflow import make_plan` 从同目录的模块引入函数；导入不执行任务。`plan = make_plan()` 调用函数，把它返回的列表放进变量 `plan`。列表中的每个元素是一份节点字典。

`for node in plan:` 按列表顺序取出一份节点，缩进的 `print` 随之执行。`node["id"]` 根据键取值；四个键的意义要与源码一致。`needs=[]` 是空列表，意思是没有其他节点结果的依赖，不是这个工具没有输入或没有权限要求。

例如草稿节点的输入表应写“政策结果、工单结果”，输出写“正文、两个来源、当前标记”，失败写“缺资料或政策过期”。这样才能判断是否能进入下一步，而不是只有一句“生成草稿”。

""",
        """## 沿输出手算执行过程

第一个 `[0]` 取场景列表的首项，也就是正常合成场景；这是一种夹具选择，换列表顺序会改变场景。`run_workflow` 返回状态字典。`trace` 是按发生顺序记录的事件列表，`dispatch` 表示把节点交给工具执行，`completed` 事件表示某一个节点完成，两者不同。

开始 `completed` 为空，policy 和 ticket 的空依赖都满足。两份结果收齐后，draft 才满足依赖。草稿完成后 review 才就绪。最后的 `status="completed"` 是整个任务终态，而 `state["completed"]` 是各节点成果的字典；相同单词出现在不同位置，要结合字段理解。

Python 中 `if event["event"] == "dispatch":` 只打印调度事件，因此你会看到三轮而不是所有日志。四次尝试来自第一轮 2 次、后两轮各 1 次。两个读取谁先返回可以变化，调度分组和依赖条件应保持一致。

### 独立操作的具体完成标准

在自己的笔记画四个方框，先连依赖，再遮住输出手算三轮。随后改环并调用校验器，检查错误应出现“无环/循环”相关信息；修复后原始任务应恢复四次尝试。改错计划的实验放在自己的练习脚本，不修改公共夹具以免后续各讲结果一起变化。

如果出现 `KeyError`，先查看是哪个键缺失；不要用空字典替代失败结果。若 `ModuleNotFoundError: workflow`，检查文件位置及终端目录。若运行一直等待，停止自己的进程，检查是否改了工具函数；校验正确的固定小任务应迅速结束。

""",
        """## 文件与状态逐步检查

`TemporaryDirectory` 创建一个由本脚本拥有的临时文件夹。`with` 结束时自动清理它；本例用于观察保存与恢复机制，不是永久保留你的业务记录。`Path(folder) / "state.json"` 用 `/` 拼接路径，Windows 下也可这样写，不是数学除法。

第一次 `run_workflow` 写入检查点并返回等待状态。`load_checkpoint` 读取磁盘的 JSON，而不是重复执行工具；第二次运行接收 `state=restored`，从成果和累计预算继续。`checkpoint_path=path` 是按名称传参数，告诉函数将新状态继续写到同一个文件。

观察结果时依次确认：等待状态是 `awaiting_approval`、次数 4、恢复后次数 5、发布结果带 `simulated_only_no_external_send`。少了最后一个检查就可能把模拟标记误认为真实发布。

要留一份用于学习的检查点，可在自己的脚本中使用新的 `Path("checkpoint-my-01.json")`，先确认文件不存在；不要覆盖自己的旧记录。先打开 JSON 看 `plan`、`completed`、`attempts` 与 `budgets`，再恢复。JSON 可以阅读，但不要手改其内容绕过等待或失败。

错误“版本/策略/场景不匹配”时，核对保存和恢复使用的同一场景、策略及代码版本，重新开始一个明确的新任务比伪造旧状态更可靠。错误“恢复预算必须一致”时传回原来的预算；如果业务确需新预算，应另开有明确授权的新任务，并保留旧报告。

""",
        """## 从反馈读到修复，而不是只看成功字样

最小代码中的 `next(...)` 表示从满足条件的场景中取第一项，`item["id"] == "primary_down"` 筛选主来源故障。若你改成不存在的 ID，会出现 `StopIteration`；先查看夹具真实 ID，不能把它当工具故障。当前生成器语法已用于已有教材，若仍陌生，可先用普通 `for` 循环查找一个匹配场景来帮助阅读。

事件中的 `failed` 解释哪一个节点失败及原因；`repair` 解释计划的改变。`reused=["ticket"]` 说明工单成果留下，而不是工单又运行了一遍。最后来源中的备用标识说明草稿确实使用了新资料；只改日志而不改依赖不算完成修复。

动手时分三次记录“场景、允许备用、上限、实际状态、尝试次数、草稿是否存在”：先跑 primary_down，再跑 both_down，最后保持 primary_down 并传 `maximum_attempts=4`。三次分别得到 completed/5、有草稿；needs_human/3、无草稿；budget_exhausted/4、有草稿但无检查成果。

如果不能解释第三种为何不成功，回到第 1 讲的验收条件：任务包括检查，不能拿中间成果冒充完整结果。迁移练习完成标准是写明“哪份结果失效、哪些下游结果要重做、哪些独立结果可以复用”，而不是只回答“重新规划”。

""",
        """## 自己核对表格的方法

运行最小示例后，先按 `status_counts` 相加，每一行必须等于 6。fixed 的三个计数是 completed=1、needs_human=4、awaiting_approval=1；另外两行分别是 3、2、1。字典的打印顺序不影响这些计数。

`completed / n` 是“满足当前完整任务目标的数量 / 所有场景数量”。人工等待可另报告为安全暂停数量，但不能同时把它加进完成数。不要把工具尝试次数当模型 token 数，更不能用 Python `None` 推断实际账单金额。

随后任选主故障与双故障两个场景，在报告 `results` 中找同一场景的三种策略，阅读 `trace`，逐个数 dispatch 中的节点数量。把失败节点也算进去，应该能解释为什么串行观察在双故障时没有读取工单，另外两种先派发工单的策略会多做一次读取。

独立练习的完成标准是给出“固定策略停止的具体原因、动态规则恢复的允许条件、额外一次调用在哪里发生、还有哪项真实模型证据缺失”四个答案。迁移练习选择固定审批流程时，必须写清输入稳定和权限固定这两个理由，而不是只说“固定更好”。

""",
        """## 将批准对象写到可以核对的程度

先写一段审批摘要：任务对象是模拟工单 T-01，拟执行操作是发布哪一版草稿，引用哪两个来源，检查结果是什么，是否会改变外部系统。当前工程最后一项明确写“无外部发送，仅内存标记”。真实业务应展示实际影响和可回滚条件，不能复用这段模拟描述冒充真实审批材料。

代码第一行输出恢复演示字典，里面有 before/after 和次数。第二部分把场景中的 `review_passed` 改成 False，故意制造检查失败；它只改变本次载入的合成字典。即使传入 `simulated_approval=True`，检查依赖也失败，所以打印是否发布为 False。

`"publish" in state["completed"]` 判断字典是否有该键，不是查看任意日志里是否出现单词 publish。确认门等待时发布还没有被尝试；检查失败时任务转到人工处理，不会到发布节点。

自己新增失败场景之前，先写预期状态、工具调用上限和禁止出现的发布结果，再运行并逐项对照。自己的报告区分“已跟做”“能独立解释”“真实系统待验证”；作者 21 项测试通过不能代替这三个学习判断。完成本讲时应能展示一次等待、一次拒绝和一次模拟恢复，并说明每一步证据。

""",
    ]
    for path, text in zip(lessons, additions, strict=True):
        insert_before(path, "## 动手", text)
    ledger = GUIDES / "课程覆盖台账.md"
    text = ledger.read_text(encoding="utf-8")
    marker = "## 模块 19："
    start = text.index(marker)
    end = text.index("\n## 模块 ", start + len(marker))
    block = text[start:end]
    block += "\n> [!warning] 当前对照的范围\n> C19-03 的本机示例仅完成三种确定性调度规则的六场景回放。真实语言模型 ReAct / 先规划策略的成功率与费用尚未测量；第 5 讲提供实验协议，不能把回放计数当成真实模型基准或学习者完成。\n"
    ledger.write_text(text[:start] + block + text[end:], encoding="utf-8")
    readme = ROOT / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("14～25、27～28", "14～25、27～29"),
        encoding="utf-8",
    )
    print("六讲操作解释与台账限制已补齐")


if __name__ == "__main__":
    main()
