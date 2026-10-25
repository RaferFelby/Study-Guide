---
title: 第 1 讲：运行Python并统计工单
tags: [lesson, python, beginner]
aliases: ["认识项目并运行 Python", "Python 工程化 01"]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：运行Python并统计工单

> [!nav] 页面导航
> 首次主线 1/11 · [[01_学习指南/01_Python工程化/00 Python 工程化学习地图#学习顺序|单元 01：Python 工程化]] · [[01_学习指南/01_Python工程化/逐讲学习/02 把函数拆成模块并运行项目|下一讲]]

## 本讲目标与操作位置

第一次先运行 `hello.py`，再用列表、字典、判断和循环统计工单。所有练习文件都在本单元 `示例工程/` 创建，使用仓库根共享解释器。一次只创建并运行一个例子。能独立改一条工单并解释计数变化，就可以继续模块课。

## 先分清编辑器、终端和 Python

你会在 VS Code 里写代码，在终端里告诉 Python 运行哪一个文件。VS Code 是编辑器，负责显示和修改文件；终端是输入命令的地方；Python 解释器则是读取 Python 代码并执行它的程序。三者会配合工作，但不是同一个东西。

### 第一次运行：让 Python 打招呼

1. 打开 VS Code，选择“文件 → 打开文件夹”，打开本单元的“示例工程”文件夹：`01_学习指南/01_Python工程化/示例工程/`。
2. 在左侧文件区空白处点右键，选择“新建文件”，命名为 `hello.py`。
3. 输入下面两行并保存。`.py` 是 Python 源码文件的常用后缀。

```python
name = "小明"
print(f"你好，{name}！")
```

第一行把文字 `小明` 放进一个叫 `name` 的变量。你可以把变量先理解为贴在一个值上的名字。第二行调用 `print` 把结果显示出来；`f"...{name}..."` 会把花括号里的变量值放进文字中。

4. 在 VS Code 顶部选择“终端 → 新建终端”。确认终端当前目录是示例工程目录，然后输入：

```powershell
..\..\..\.venv\Scripts\python.exe --version
..\..\..\.venv\Scripts\python.exe hello.py
```

第一条命令查看共享环境的 Python 版本，第二条让同一个解释器运行当前目录中的 `hello.py`。预期能看到类似：

```text
Python 3.13.12
你好，小明！
```

版本号可能不同。若提示找不到指定路径，先在终端输入 `Get-Location`，确认当前目录是本单元的“示例工程”，再用 `Test-Path ..\..\..\.venv\Scripts\python.exe` 检查共享解释器是否存在；`True` 表示路径存在，`False` 表示当前目录或环境路径需要核对。只有确认根目录没有环境时，才按 [[90_参考与维护/01 使用与环境/01 共享Python环境与运行约定#共享 Python 环境|共享环境说明]]准备安装方案并获得批准。若出现 `can't open file`，检查文件是否已保存、是否误命名为 `hello.py.txt`，以及终端是否在保存文件的目录。

> [!info] 一个重要习惯
> 命令里的相对路径从“终端当前目录”开始算，不会自动从你正在看的文件位置开始算。遇到找不到文件时，先检查当前位置，再检查拼写。



## 看懂变量、函数和字典

Python 程序通常由一条条语句组成。赋值语句 `status = "open"` 把右侧的值绑定到左侧名字；函数把一组有名字的步骤装起来，之后可以用函数名重复调用。

```python
def describe_ticket(ticket_id, status):
    return f"工单 {ticket_id} 当前状态：{status}"

message = describe_ticket("T001", "open")
print(message)
```

逐步读：`def` 开始定义一个函数；`describe_ticket` 是函数名；括号里的 `ticket_id` 和 `status` 是参数，也就是调用函数时要提供的输入；冒号后的缩进内容属于函数；`return` 把结果交还给调用者。最后两行调用函数并打印它返回的文字。

函数调用时，实际提供的值叫“实参”。所以 `describe_ticket("T001", "open")` 里的两个文字分别交给两个参数。函数内部名称与外部变量可以不同，但按位置传值时顺序要一致。

### 两种常用容器：列表和字典

列表用来按顺序放多个值；字典用来通过“键”找到对应的“值”。下面的工单清单是一个列表，每张工单用字典记录编号和状态：

```python
tickets = [
    {"ticket_id": "T001", "status": "open"},
    {"ticket_id": "T002", "status": "closed"},
]

for ticket in tickets:
    print(ticket["ticket_id"], ticket["status"])
```

`for ticket in tickets` 表示依次把列表中的每个字典交给变量 `ticket`。`ticket["status"]` 按键读取状态。运行结果是两行：

```text
T001 open
T002 closed
```

当程序需要统计每种状态有多少张工单时，可以使用字典累计计数。下面是独立可运行版本，另存为 `count_demo.py`：

```python
tickets = [
    {"ticket_id": "T001", "status": "open"},
    {"ticket_id": "T002", "status": "closed"},
]

def count_status(tickets):
    counts = {"open": 0, "closed": 0}
    for ticket in tickets:
        status = ticket["status"]
        counts[status] = counts[status] + 1
    return counts

print(count_status(tickets))
```

开始时两种状态的数量都是 0。每读到一张工单，就把它对应的计数加 1。结果是 `{'open': 1, 'closed': 1}`。右侧 `counts[status] + 1` 先读取旧数值并加一，再把结果放回左侧对应位置。Python 用缩进划分函数和循环，不用大括号划分代码块；这里的 `{}` 建立字典，之前 f 字符串内部的 `{name}` 才是格式占位。

> [!warning] 为什么要检查外部数据
> 如果某张工单没有 `status` 这个键，`ticket["status"]` 会报 `KeyError`；如果状态拼成 `"opne"`，右侧读取 `counts["opne"]` 也会报 `KeyError`，不会自动新增类别。直接赋值 `counts["opne"] = 1` 才会添加新键。用户文件、网络响应和数据库内容都是外部数据，不能假设它们一定正确。

### 在计数前作判断

现在希望错误能明确告诉我们“状态无效”。先在同一目录新建 `check_status_demo.py`，保存并运行这个完整例子：

```python
ticket = {"ticket_id": "T001", "status": "open"}
counts = {"open": 0, "closed": 0}
status = ticket.get("status")
if status not in counts:
    raise ValueError("工单缺少有效的 status")
counts[status] = counts[status] + 1
print(counts)
```

`ticket.get("status")` 是字典提供的取值操作，缺少该键时返回 `None`，表示此处没有取到值。`status not in counts` 检查状态是否不在字典的键中，结果是布尔值 `True`（是）或 `False`（否）。`if` 只在条件为 `True` 时执行缩进的语句；`raise ValueError(...)` 主动报告值不符合要求，此处没有接住错误，程序就停止。合法状态跳过报错语句，继续计数。之后看到整数计数的 `counts[status] += 1`，可以在这个例子中理解成上面的加一赋值。

运行 `..\..\..\.venv\Scripts\python.exe check_status_demo.py`，先得到 `{'open': 1, 'closed': 0}`。把 `open` 改成 `opne` 再运行，最后一行应为 `ValueError: 工单缺少有效的 status`；删掉 `status` 字段也应同样失败。一次只改一种情况，检查后恢复合法样例。报错验证的是拒绝坏数据，不应继续打印成功计数。异常如何接住和补充原因，见 [[01_学习指南/01_Python工程化/逐讲学习/06 看懂报错并安全管理资源|第 6 讲：看懂报错并安全管理资源]]。

判断是否相等写 `==`，例如 `status == "open"`；单个 `=` 用于赋值。`if` 后不要漏冒号，内部使用四个空格缩进。成功标准：你能解释合法输入为何绕过 `raise`，以及未知状态为何在计数前停止。

## 跟做练习：创建一个小工单统计程序

1. 在 VS Code 中打开单元 01 的“示例工程”目录，并在其中新建 `first_tickets.py`。
2. 手动输入两张工单的列表和统计函数，不要复制 `ticketkit` 里的文件。
3. 在示例工程目录的终端运行 `..\..\..\.venv\Scripts\python.exe first_tickets.py`。这是从该目录调用仓库根目录共享虚拟环境的 Python 解释器；如果提示找不到解释器，先确认当前目录和根目录 `.venv` 是否已创建。
4. 再添加一张 `closed` 工单，确认关闭数量增加。

提示：先建立 `counts` 字典，再用 `for` 逐张处理。你需要决定遇到未知状态时是报错，还是单独统计；本练习选择报错。

> [!example]- 跟做练习参考答案与解析（先完成再展开）
> ```python
> tickets = [
>     {"ticket_id": "T001", "status": "open"},
>     {"ticket_id": "T002", "status": "closed"},
>     {"ticket_id": "T003", "status": "closed"},
> ]
>
> def count_status(rows):
>     counts = {"open": 0, "closed": 0}
>     for row in rows:
>         status = row.get("status")
>         if status not in counts:
>             raise ValueError("工单缺少有效的 status")
>         counts[status] += 1
>     return counts
>
> print(count_status(tickets))
> ```
> 输出应为 `{'open': 1, 'closed': 2}`。`.get("status")` 在字段缺失时给出 `None`，于是检查会报出我们写的错误。本次先使用普通函数；类型标注在第 3 讲说明。

## 独立练习：从空文件完成计数

关闭答案，写两张 open 工单和一张 closed 工单，得到 open=2、closed=1。再删掉一张工单的 status，检查程序在计数前拒绝它。完成标准是能解释每次循环怎样更新 counts。

> [!example]- 提示与参考思路
> 先固定两个计数器为 0；循环读取 status，缺失或不属于两类就报错，否则加一。正常输出为 `{"open": 2, "closed": 1}`；缺字段时应抛出清楚的 ValueError。可用上方跟做函数核对，不新增分支掩盖错误。

## 迁移练习：统计两种文件处理结果



离开工单场景：用 `results = ["ok", "failed", "ok"]` 表示三个文件的处理结果，写 `count_results(results)`，得到 `{'ok': 2, 'failed': 1}`。不要复制整套 Ticket 类。提示：输入项已经是字符串，直接用它作为计数字典的键。

完成标准：空列表得到两个 0；加入 `"unknown"` 后明确报错；能说明“合法类别先固定、计数前校验”的步骤为什么可以复用。

> [!example]- 迁移练习参考答案
> ```python
> def count_results(results):
>     counts = {"ok": 0, "failed": 0}
>     for result in results:
>         if result not in counts:
>             raise ValueError("文件处理结果必须是 ok 或 failed")
>         counts[result] += 1
>     return counts
>
> print(count_results(["ok", "failed", "ok"]))
> print(count_results([]))
> ```
> 保存为 `file_results.py`，运行共享解释器加文件名。两行依次为 `{'ok': 2, 'failed': 1}` 和 `{'ok': 0, 'failed': 0}`。再把第一组的 `failed` 改成 `unknown` 检查拒绝路径。算法没有依赖“工单”这个名字，只依赖有限类别和逐项累加。

## 继续学习

> [!next] 下一步
> [[01_学习指南/01_Python工程化/逐讲学习/02 把函数拆成模块并运行项目|首次主线下一步：把函数拆成模块并运行项目]]

> [!info]- 练习与记录
> [[01_学习指南/01_Python工程化/示例工程/README#代码导航（VS Code）|查看源码]] · [[01_学习指南/01_Python工程化/示例工程/README#安装与运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 01：Python 工程化|本单元完成清单]]
> [[00_学习路线/01 从零开始建立共同基础|回看首次学习阶段]]
