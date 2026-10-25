"""记忆与上下文管理详细教材。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/28_记忆与上下文管理"
MAP = "00 记忆与上下文管理学习地图"
LESSONS = [
    "01 区分临时上下文长期偏好与外部知识",
    "02 给记忆写入确认来源与用户范围",
    "03 检索纠错去重并处理过期记忆",
    "04 删除用户记忆并核查残留范围",
    "05 按token预算压缩历史而非截断问题",
    "06 用命中误记与删除Case验收记忆",
]


def write(name, body, title=None):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {title or path.stem}\ntags: [learning, memory, context]\nupdated: 2026-10-11\n---\n\n# {title or path.stem}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../27_推理服务与性能工程/00 推理服务与性能工程学习地图|前一单元]]"
    )
    following = (
        f"[[{LESSONS[index + 1]}|下一讲]]" if index < 5 else f"[[../{MAP}|返回地图]]"
    )
    write(
        f"逐讲学习/{LESSONS[index]}.md",
        f"[[../{MAP}|单元地图]] · {previous} · {following}\n\n" + body,
    )


if __name__ == "__main__":
    lesson(
        0,
        r"""
## 本讲要解决的问题与前置

助手“记住我偏好中文”与“查到公司的退款政策”不是同一件事。把个人偏好、临时猜测和业务规则混在一起，会出现过期事实、跨用户泄漏及错误权限。本讲先分清边界，之后才实现记忆。

前置：Python字典、文件运行；[[../../12_RAG数据工程/00 RAG 数据工程学习地图|资料来源]]与 [[../../17_SQL数据库与数据集成/00 SQL 数据库与数据集成学习地图|SQLite基础]]。不熟可先看地图对应讲解。本例所有用户、时间和对话均合成，没有LLM、向量库或真实个人资料。阅读顺序：分类 → 跑演示 → 看数据流 → 做练习。

## 概念与直觉：当前桌面、个人笔记、官方档案

工作记忆是本次任务的临时状态，如当前问题、最近几轮对话、未完成步骤；对话摘要是把较早内容有损压缩，方便放入有限输入；长期记忆跨会话保留一些经确认的用户经历/偏好，有明确来源、时间及删除机制。

RAG外部知识是从受治理的资料库检索内容，如公司发布的政策；业务数据库是订单、权限、账户状态等系统记录。这些通常由业务负责人更新、校验和控制访问，不由用户随口一句或模型猜测覆盖。

桌面/笔记/档案的类比只说明使用位置；实际机制是不同存储、数据owner、更新来源与检索权限。长期不意味着永远正确或永不删除；摘要也不等于原文，不能作为完整审计记录。

## 最小操作：先跑合成演示

VS Code打开本单元示例工程，选择根目录共享.venv，终端运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py
```

无需新增依赖。程序在当前工程创建自己的临时SQLite，结束关闭连接并清理，只输出合成报告。预期origin标为synthetic，first为created/version1，duplicate为unchanged/version1，correction为updated/version2；alice当前偏好English，bob为Spanish。你还没有输入真实偏好，这些不代表系统记住了你。

## 最小示例：读报告的职责

工程内新建 `lesson_01.py`：

```python
from demo import run_demo

report = run_demo()
print("来源：", report["origin"])
print("纠错后记忆：", report["hit"][0]["value"])
print("压缩前后：", report["context"]["before_tokens"], report["context"]["input_tokens"])
print("删除后命中：", report["alice_hits_after"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_01.py`。预期English、2663→592、删除后[]。预算使用本例UTF-8字节教学Tokenizer，不是任何实际大模型token数；第5讲详解。

## 逐步数据流与当前必须掌握的边界

1. 用户确认偏好后，写入带owner、source、time、confidence的记录。
2. 下一任务先按当前可信用户范围读取未过期记忆；记忆作为数据加入上下文，不作为系统权限。
3. 当前问题与必要固定结构先保留，为输出预留空间；超预算时压缩旧历史。
4. 用户纠正旧偏好，用新来源和版本更新；要求删除时删该用户当前记录及事件，后续检索不得再命中。

本例只支持preferred_language、answer_style、context_goal三类偏好键，不存密码、政策或系统角色。语义向量检索、复杂画像、自动偏好提取是进阶，当前先掌握确定性生命周期。

## 动手、常见错误与练习

在学习记录把“我喜欢短答案”“本次任务进行到步骤2”“退款政策v3”“用户拥有管理员权限”“模型猜测用户喜欢英文”逐项归类。别把最后一项直接写为长期事实；不要用真实隐私增加演示真实感。

### 跟做：归类三种数据

完成标准是每种写存储来源与更新者。

> [!example]- 参考答案与解析
> 短答案偏好由本人确认后可入长期记忆；步骤2属临时任务状态；退款政策由政策系统/RAG资料库治理。管理员权限由身份/业务系统判定，不能从偏好记忆取得。

### 独立：摘要漏了金额怎么办

摘要只保留目标，原对话有金额与日期，能据摘要执行付款吗？

> [!example]- 参考答案与解析
> 不能。摘要有损，需回到可授权的原始记录或明确询问，付款还需业务校验与审批。压缩不是凭空补全丢失事实。

### 迁移：旧记忆与当前指令冲突

旧偏好中文，本次明确要英文，怎样处理？

> [!example]- 参考答案与解析
> 本次明确指令优先决定本次回答；是否长期改偏好需另外确认。不能自动把一次任务要求写成永久偏好，也不能让旧偏好覆盖当前问题。
""",
    )

if __name__ == "__main__":
    lesson(
        1,
        r"""
## 本讲要解决的问题与前置

没有出处的“记忆”很难纠错，也可能属于另一个用户。本讲写第一条带范围的偏好。前置是上一讲的边界、日期与SQLite入门；读memory.py的write与connect。

## 概念与字段

owner是记录所属用户范围，本例alice/bob均虚构。真实服务应由可信身份取得owner，不能信请求body随意给的用户ID；本工程没有登录系统。key是偏好种类，value是内容；source是原确认消息引用；source_time是来源时间；updated_at为本次更新时间；expires_at为到期时间；version是修订编号。

confidence是置信度标签0～1，本例由数据方案给出0.95，未训练校准器，不是“95%保证正确”。confirmed=True表示调用者已经取得明确确认，程序无法通过这个布尔量证明真人同意；迁移时要保存可检查的确认流程。

## 最小示例与操作

VS Code工程新建 `lesson_02.py`：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
from memory import MemoryStore

now = datetime(2026, 10, 11, tzinfo=timezone.utc)
with TemporaryDirectory(dir=Path.cwd()) as folder:
    store = MemoryStore(Path(folder) / "memory.sqlite3")
    result = store.write("alice", "preferred_language", "Chinese",
                         "conversation-1/message-1", now, now,
                         confirmed=True, ttl_days=30)
    row = store.retrieve("alice", now)[0]
    print(result)
    print(row["owner"], row["source"], row["version"], row["expires_at"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`。预期created/version1，alice、conversation-1/message-1、1，到期2026-11-10的UTC时间。TemporaryDirectory只创建并清理自己的临时文件；不删除工作区已有用户文件。

## 逐步讲解

datetime表示日期时间，timezone.utc使时区明确；没有时区会被拒绝，避免混用本地与UTC比较。示例时间合成，方便重复验证，不代表真实聊天发生日期。ttl_days为保留有效天数，本例范围1～365，是教学选择，不是隐私法规统一期限。

MemoryStore首次建两张表：memories保存当前偏好，主键为(owner,key)；events只记类型/版本/时间，不保留旧value。参数化SQL使用?传值，避免把文本拼成SQL语句。write先校验再开始事务，错误输入不会部分写入。

BEGIN IMMEDIATE先取得写事务，再读取版本和写入，让并发写者串行更新；没有承诺“最后提交必然是业务最新事实”，还需时间与来源规则。库调用返回created/updated/unchanged，学习者应检查状态而不是只看函数没报错。

## SQLite连接为何需要额外关闭

`with sqlite3_connection:`管理事务提交/回滚，不自动关闭连接；本工程connect使用contextmanager，内部事务结束后finally执行connection.close。作者初版曾因连接未关而在Windows清理临时文件时报WinError32，修复后有专门删除文件测试，不用忽略错误掩盖资源泄漏。[Python3.13 SQLite文档](https://docs.python.org/3.13/library/sqlite3.html#how-to-use-the-connection-context-manager)说明该区别。

contextmanager把yield之前视作准备，yield交出连接供with内代码使用，退出后执行收尾。它只是让资源生命周期明确，不是每个小函数都必须套框架。

## 动手与预期

将confirmed改False，应明确拒绝“长期写入需要确认”；恢复True才成功。把key改system_role应拒绝；恢复preferred_language再运行。到期有效不代表物理删除，第4讲会区分。

常见错误：时间未带tzinfo；把confidence0.95当可靠认证；把owner从未经认证的参数直接接入；密码当偏好保存。先确定范围和确认来源，再添加更多存储功能。

## 练习与完成标准

### 跟做：列出一条完整记录

打印source_time、updated_at、confidence、expires_at。完成标准是能解释每个字段。

> [!example]- 参考答案与解析
> 来源时间描述依据，更新描述存储操作时间，置信度是方案标签，到期描述检索有效期限。它们不是同一个概念。

### 独立：来源在未来

将source_time设置比now晚一天，会怎样？

> [!example]- 参考答案与解析
> 拒绝，不写入。检查时区与数据时钟，不能允许未来确认覆写当前记录后继续宣称可追溯。

### 迁移：自然语言自动提取

模型从聊天猜出用户爱简短，能直接confirmed=True吗？

> [!example]- 参考答案与解析
> 不能。先作为待确认假设，在获得明确确认后写入；模型判断与用户授权分开。假设可留当前工作记忆，但不伪装长期事实。
""",
    )

if __name__ == "__main__":
    lesson(
        2,
        r"""
## 本讲要解决的问题与前置

用户纠正偏好、同一记录重复写、偏好到期时，怎样检索当前可信版本？前置第2讲字段与事务；读write的previous分支和retrieve的WHERE。

## 概念与检索条件

本例检索按owner过滤、到期时间严格大于now、更新时间不晚于now、confidence至少0.8。没有向量语义匹配，只有确定性筛选；0.8是教学阈值，不是经校准证明的最佳值。过期记录不进入当前上下文，但仍留数据库，直到明确删除。

同一value、source、source_time、confidence且未过期才unchanged，版本不增加、到期不刷新；不同确认来源或置信度即使value相同也会更新版本。纠错用较新来源时间，旧消息不能覆盖较新确认。相同时间并发仍按写事务顺序，复杂冲突留进一步治理。

## 最小示例：纠错与隔离

工程新建 `lesson_03.py`：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone
from memory import MemoryStore

now = datetime(2026, 10, 11, tzinfo=timezone.utc)
with TemporaryDirectory(dir=Path.cwd()) as folder:
    store = MemoryStore(Path(folder) / "memory.sqlite3")
    args = ("alice", "preferred_language", "Chinese", "message-1", now, now)
    print(store.write(*args, confirmed=True))
    print(store.write(*args, confirmed=True))
    later = now + timedelta(minutes=1)
    print(store.write("alice", "preferred_language", "English", "message-2",
                      later, later, confirmed=True))
    print(store.retrieve("alice", later)[0]["value"])
    print("bob命中：", store.retrieve("bob", later))
    print("到期后命中：", store.retrieve("alice", later + timedelta(days=31)))
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`，预期created1、unchanged1、updated2、English、bob[]、到期[]。`*args`将tuple逐项作为位置参数，内容仍是第2讲同样的六个值，不是隐藏状态。

## 逐步理解错误记忆

示例最初Chinese后来被纠正为English。这是对记忆内容的模拟纠错，不意味着用户真的改变偏好。源message-2与version2可追溯，旧value不保留在events，避免为了审计形成另一份敏感内容影子副本。

假设旧message-1在网络延迟后又到达，source_time早于当前记录，write明确失败。不要捕获后说unchanged，因为冲突与合法重复不同。当前明确指令优先于旧记忆；如果只针对一次回答，未必应更新长期偏好。

检索返回每条完整metadata。上下文编译器只携带key/value/source必要数据，时间过滤已经由retrieve负责。生产中不能允许调用者绕过过滤直接塞过期记忆；本例compiler验证owner，但未实现身份认证和全流程权限。

## 动手：低置信度与新确认

把第一条confidence设0.5，retrieve默认应返回[]；再用新message确认并写0.95，版本增加，重新检索可命中。这不是模型自动变可靠，而是模拟数据治理的明确更新。

到期边界用 `now + timedelta(days=30)` 检查第一条若未纠错应无命中，等于expires_at也算过期。提前读取更新时间之前不会看到未来记录，便于发现时钟数据问题。

## 常见错误与练习

重复写无限延长TTL：本例同来源重复不刷新。纠错仅在prompt里加英文却数据库仍中文：需要明确长期更新并检索核查。只用key不带owner查询：可能跨用户，检查所有SQL条件。把过期无命中说已经删除：区分逻辑有效性与存储清除。

### 跟做：标记三种写入状态

完成标准是版本1、1、2，来源与更新时间匹配。

> [!example]- 参考答案与解析
> 重复不改变事实与依据，因此unchanged；较新内容确认才更新。来源时间不同但内容相同也可更新依据，不是单纯按value去重。

### 独立：0.79为什么没命中

能因此断言事实一定错误吗？

> [!example]- 参考答案与解析
> 低于本例0.8门槛而未纳入，不证明真假。需要检查来源或再确认；标签阈值只是治理策略，不能代替事实核验。

### 迁移：两条偏好互相冲突

同一时间两来源一个要求短一个要求详细，怎样说明限制？

> [!example]- 参考答案与解析
> 本例同时间按事务后写覆盖，仅展示确定性版本，不解决语义冲突。真实方案应依据最新明确确认或询问用户，并保留当前任务范围，不能凭模型猜测哪条更重要。
""",
    )

if __name__ == "__main__":
    lesson(
        3,
        r"""
## 本讲要解决的问题与前置

“忘掉我的偏好”不能只让下次回答不提它。本讲实际删除指定用户当前记忆及本例事件，检查其他用户不受影响，并说明未覆盖副本。前置是第3讲owner、检索、到期；读memory.py的delete与event_count。

## 概念：到期、逻辑删除、完整清除不是同一层

TTL到期表示当前检索不再使用，数据仍可能在表里；本例delete执行SQL删除当前记录和该用户事件。它验证后续查询不命中，不保证磁盘取证级擦除、所有旧备份、原对话、日志或已经生成的回答都消失。

没有缓存/向量索引时删除范围较小；未来如果有这些副本，需要定义同步失效与删除状态。不要将当前SQL行删除说成全系统“彻底忘记”。这里仅合成数据，用来练明确边界，不录入真实敏感信息。

## 最小示例：只删alice

工程新建 `lesson_04.py`：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
from memory import MemoryStore

now = datetime(2026, 10, 11, tzinfo=timezone.utc)
with TemporaryDirectory(dir=Path.cwd()) as folder:
    store = MemoryStore(Path(folder) / "memory.sqlite3")
    for owner, value in [("alice", "Chinese"), ("bob", "Spanish")]:
        store.write(owner, "preferred_language", value, "synthetic-message",
                    now, now, confirmed=True)
    print("删掉条数：", store.delete("alice"))
    print("alice：", store.retrieve("alice", now), store.event_count("alice"))
    print("bob：", store.retrieve("bob", now)[0]["value"])
    print("重复删除：", store.delete("alice"))
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_04.py`。预期1、[]和0、Spanish、第二次删除0。0表示当前已无记录，不等于失败；不能为了让每次打印1而重新创建记录。

## 逐步讲解与用户范围

delete的key为空时删该owner所有当前偏好；给preferred_language时只删这一键。条件语句由程序在两个固定模板中选择，用户值仍使用?绑定，不拼接任意SQL。一个事务内删除memories和events，失败时回滚，避免删了内容却留一半事件。

本例events从来不存旧value，但仍按用户删除metadata。查询bob验证隔离，不只检查总表空了；如果把DELETE WHERE owner遗漏，两个用户都可能被误删。

真实删除请求的owner应来自当前登录身份，用户不能在工具参数里改owner去删除别人。这个脚本没有登录界面，内部API接受调用者指定owner，所以测试证明SQL条件行为，不证明未经认证的调用者被阻止。应用层需要受信范围封装。

## 动手：删除后重建上下文

用 `store.retrieve("alice", now)` 的新结果传入compile_context，应不再出现该偏好。已经创建过的Python变量、打印过的报告或旧对话不自动被清空。本工程演示报告为了教学保留“删除前命中”的合成快照，明确不是现实个人数据删除系统。

写一份删除范围说明：当前memory表、事件表已删；缓存/向量索引本例无；原对话和外部备份本例没有实现治理；旧报告仅合成，不声称自动抹除。不要随意扫描或删除其他工作区资料来模拟遗忘。

## 常见错误与练习

到期无命中叫删除完成：用delete和查询检查。删除当前表忘事件：同事务处理。只测试alice不检查bob：补隔离Case。删除后复用旧compiled_prompt：重新取有效数据组装，必要时失效已缓存上下文。

### 跟做：重复删除

完成标准是第一次1、第二次0，bob不变。

> [!example]- 参考答案与解析
> 对当前存储删除是幂等的：多做一次不会创造数据或错误删别人。这不意味着所有外部副本的删除也已完成。

### 独立：只删一个偏好

再写answer_style，删除preferred_language后判断剩余。

> [!example]- 参考答案与解析
> `store.delete("alice", "preferred_language")`只删除语言键，answer_style仍可检索。测试同时核查事件条件，不能把整个用户数据删空来冒充按键删除。

### 迁移：向量库的记忆

写出完整删除请求涉及的副本与验证。

> [!example]- 参考答案与解析
> 主存储、向量记录、缓存、摘要与权限允许处理的源对话/备份策略；检查按用户检索不再命中、缓存失效、任务中旧上下文是否停止使用。明确保留/删除期限及未能清除项，不能只说“删了embedding”。
""",
    )

if __name__ == "__main__":
    lesson(
        4,
        r"""
## 本讲要解决的问题与前置

长对话超过模型窗口前，需要决定保留哪些信息。本讲精确计算当前教学Tokenizer下的输入，预留输出，再压缩旧历史；不截断当前问题或系统固定结构。前置是第1讲三种记忆和 [[../../10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|Tokenizer与模板]]。

快速顺序：先算预算 → 看计数器范围 → 运行编译 → 查看被移除来源 → 看损失 → 练习。读context.py的serialize_prompt、summarize_history、compile_context。

## 预算的最小算术

上下文窗口是一次模型调用能承载的输入加生成位置上限，实际值必须核对目标模型。本例人为设置768教学token，输出预留96、余量32，所以输入最多640。余量用于避免紧贴极限；其大小是教学选择，不是所有模型标准。

ByteTokenizer把UTF-8每个字节视为一个教学token，因此英文hi为2，中文你好为6。它只是明确且可测的计数协议，不是常见LLM的子词Tokenizer，也不是按中文字符数估计。真实接入必须用该模型Tokenizer，把角色、特殊token和聊天模板都计入，再为输出预留空间。

## 最小示例与操作

工程新建 `lesson_05.py`：

```python
import json
from context import ByteTokenizer, compile_context
from demo import make_history

tokenizer = ByteTokenizer()
print("hi与你好：", len(tokenizer.encode("hi")), len(tokenizer.encode("你好")))
result = compile_context([], make_history(), "What should I study next?", "alice")
payload = json.loads(result["prompt"])
print("输入：", result["input_tokens"], "上限：", result["input_capacity"])
print("移除轮次：", len(result["removed_turn_ids"]))
print("当前问题：", payload["current_user"])
print("摘要：", result["summary"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`，第一行2/6，输入必须≤640，移除若干偶数条旧turn，当前问题完整保留。这里没传偏好，所以数值不同于demo带记忆的592；先检查条件，不强行把两组数写成一样。

## 逐步讲解：预算先于调用

1. 校验window/output_reserve/margin为正整数且有输入空间；校验当前输入、历史字段、成对角色和用户记忆范围。
2. 用同一serialize_prompt组装固定系统字段、memory_data、summary_data、recent_history、current_user，计数涵盖JSON结构，而不是只数用户文字。
3. 如果最小固定结构加当前问题已超640，明确BudgetExceeded，要求缩短/拒绝；不偷偷砍掉当前问题尾部，尤其那里可能有约束或金额。
4. 否则每次移除最早的一对user/assistant，重新生成旧段摘要并重数，直到能放下。原始history列表不被修改。
5. 所有旧历史都移除仍超预算时，可以弃摘要，再弃部分可选记忆，并返回history_summary_dropped及dropped_memory_keys。它不是无损压缩，删除信息必须可见。

本例输出只是待调用上下文，没有LLM生成，因此预留96不验证真实模型最大生成限制；迁移时还需把同一数值传到后端生成上限。token计数必须和实际最终发送模板一致，不能计一个JSON却发送另一串chat模板。

## 摘要保留什么、丢掉什么

规则摘要只从较早user文本提取以 `goal:` 开头且≤80字符的目标，最多最近三种，带source_id；其他内容只计omitted_turns，不声称已总结。重复目标去重并指向最近来源。这个简单方法用于检查来源与损失，不是通用对话总结器。

demo的24条历史从2663字节token压到592，移除22条，保留最后user/assistant对，摘要保留目标和u-9来源。历史金额、日期、例外条件如果未按规则保留就丢失，执行高影响任务必须检索原文或确认，不能从摘要猜补。

JSON把记忆与摘要放在数据字段，但这不是抵抗模型提示注入的安全保证。本例没调用LLM，所以只能检查数据布局；权限/工具边界还由应用代码执行，不让记忆中的“忽略限制”获得系统权力。

## 动手与常见错误

把window降到300、reserve40、margin20；结果应≤240，可能summary被弃，报告标记要查看。把current改为1000个x应报BudgetExceeded；恢复后运行正常。未出错不表示记忆全部保留，检查丢弃字段。

错误做法：按字符数假装真实token；不预留输出；先发请求等超限再砍；只保留最后任意N字符导致角色/句子被切断；摘要把猜测当事实；丢信息却报告“完整历史已保留”。按步骤先预算、后选择、再核查来源。

## 练习与完成标准

### 跟做：预算恒等式

验证input_tokens+output_reserve+margin≤window。完成标准是明确tokenizer名称和实际序列化口径。

> [!example]- 参考答案与解析
> 默认上限640=768-96-32。demo的592+96+32=720≤768，剩48余量；不是某商业模型窗口大小。

### 独立：窗口1024

输出预留200、余量24，输入多少？

> [!example]- 参考答案与解析
> 800。计入系统、记忆、摘要、角色模板和当前问题全部输入；不能再给每部分各800。

### 迁移：模型总结器

若用LLM生成摘要，还需检查什么？

> [!example]- 参考答案与解析
> 原文来源、事实是否被改写/遗漏、猜测标记、隐私、摘要长度与成本、角色注入边界及版本。保留可回查依据和错误Case，不能因为“模型生成”就默认忠实或安全。
""",
    )

if __name__ == "__main__":
    lesson(
        5,
        r"""
## 本讲要解决的问题与前置

记忆能命中不够，还需证明错误内容可纠正、他人数据不混入、删除后不再使用、预算有边界。本讲完成验收与一页报告。前置是前五讲已操作，不以作者测试取代亲自练习。

## Case与预期先写清

Case是一个具体场景，包含输入、之前状态、操作、预期和实际结果。当前至少检查：经确认写入命中；未确认拒绝；合法重复不增版本；故意错误偏好经源复核后纠正；旧来源不能覆盖新版本；过期不命中；alice不能检索bob；删除后当前表/事件为空且bob保留；超预算旧历史压缩；当前问题过大拒绝。

fixtures/confirmations.json保存模拟确认消息。第一条原文期望English，demo故意误写Chinese，模拟提取错误；第二条确认纠正，version2改为English。store只校验字段与时间，不能独立理解原文真假，所以有source和confidence仍可能误记。报告的wrong_memory_case明确标记固定夹具复核，不声称真实模型发现或真人反馈。

## 最小示例：检查验收摘要

工程新建 `lesson_06.py`：

```python
from demo import run_demo

report = run_demo()
case = report["wrong_memory_case"]
print("期望/误记/纠正：", case["source_expected"], case["mistaken_value"], case["corrected_value"])
print("删除后记录与事件：", len(report["alice_hits_after"]), report["alice_events_after"])
print("另一个用户保留：", len(report["bob_hits_after"]))
context = report["context"]
print("预算满足：", context["input_tokens"] <= context["input_capacity"])
print("压缩方法：", context["summary"]["method"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_06.py`，预期English/Chinese/English、0/0、1、True、rule_extract_goals_only_lossy。它检查模拟流程，未评价真实对话模型忠实度。

## 动手：读一个测试，再独立增加Case

VS Code打开tests/test_memory.py的test_user_scope_delete_and_event_cleanup，顺着“准备alice/bob→删除alice→查询两人→编译新上下文”解释每个断言。测试要求删除后未来上下文不包含Chinese，但没有声称以前打印的合成报告自动消失。

在工程终端运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
```

pytest是已有共享测试工具，tests指定本单元目录，-q精简输出；没有工具先检查环境并提出安装方案，不新建单元环境。作者24项通过，含并发版本与Windows文件关闭检查，自己的结果如实记录；测试通过仅覆盖这些Case。

独立增加一条“同内容但较新确认来源”测试，断言版本增加且source更新；或“只删answer_style后语言仍在”。先写预期，再执行，错误时检查是否把删除条件扩大或重复规则简化。

## 一页学习报告怎么写

写清：问题、三种记忆/RAG/业务边界、合成数据与来源、owner的可信获取责任、确认与置信标签、时间/TTL/版本规则、错误纠正Case、删除范围及副本限制、Tokenizer名称/输入预算/压缩前后、摘要保留和遗漏内容、已运行与未运行项。

结论示例应是“本机SQLite生命周期及教学字节预算通过固定Case，未验证真实LLM摘要、语义检索、生产身份或所有副本删除”。如果自己的某Case失败，列实际结果与原因，不复制作者“通过”填空。

## 记忆与RAG、业务数据的治理对照

| 数据 | 来源与更新 | 检索范围 | 失效/纠错依据 |
| --- | --- | --- | --- |
| 用户偏好记忆 | 本人明确确认，允许撤回 | 当前可信用户 | 新确认、TTL、删除请求 |
| 对话工作状态/摘要 | 当前任务/历史片段，有损来源 | 当前会话和任务 | 任务结束、源纠错、预算变化 |
| RAG外部政策 | 政策负责人发布及版本 | 资料权限与受众 | 文件更新、撤回、索引重建 |
| 订单/权限数据库 | 业务系统与授权流程 | 业务账户与服务权限 | 事务、状态变更、权限同步 |

这里没有“谁更高级”；按用途选可信源。退款天数不能由偏好覆盖，管理员权限不能由摘要授予，曾问过某话题也不能推断长期个人事实。

## 常见错误与练习

命中率高就质量好：错误记忆也能很容易命中。隐私删除只删缓存：核查主表、事件、索引与副本。摘要覆盖所有旧事实：查看method与遗漏范围。数据库校验通过就source语义正确：人工或对应验证器对照原文。

### 跟做：解释误记Case

完成标准是说出原文English、故意写Chinese、复核纠正English，且确认均模拟。

> [!example]- 参考答案与解析
> 此Case说明存储元数据完整不保证提取语义正确；固定fixture给了可回查依据。系统没调用LLM，也没有真的获取学习者同意。

### 独立：制定三个优先测试

只允许先测三项，你如何选择？

> [!example]- 参考答案与解析
> 可优先用户隔离、错误纠正、删除后不命中，因为影响范围和持久性高；随后预算超限与过期。具体排序应结合业务风险，不能用命中演示代替失败路径。

### 迁移：是否需要长期记忆

一个只查公开政策的匿名工具，必须加记忆吗？

> [!example]- 参考答案与解析
> 不一定。若每次独立查询已足够，RAG与当前会话可能更简单；长期记忆增加授权、误记、失效和删除成本。出现明确跨会话需求再引入，并测试其实际收益。

## 后续

[[../参考工程验证记录|作者验证与限制]]。下一单元规划：规划工作流与重新规划，待编写。
""",
    )

if __name__ == "__main__":
    write(
        f"{MAP}.md",
        r"""
## 从哪里开始

先打开 [[逐讲学习/01 区分临时上下文长期偏好与外部知识|第1讲]]，在VS Code示例工程运行demo.py，确认origin为合成。第一步完成判断：能将偏好、任务状态、官方政策与权限分到正确来源，不直接把猜测写为永久记忆。

## 六讲顺序

"""
        + "\n".join(
            f"{i + 1}. [[逐讲学习/{name}|{name}]]" for i, name in enumerate(LESSONS)
        )
        + r"""

## 前置与操作

[[../17_SQL数据库与数据集成/00 SQL 数据库与数据集成学习地图|SQLite和事务]]、[[../10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|Tokenizer]]、[[../12_RAG数据工程/00 RAG 数据工程学习地图|资料来源]]。文档Obsidian，代码VS Code；根共享.venv，标准库、不安装新包。

## 会得到什么

SQLite偏好生命周期、模拟确认来源、错误纠正/去重/到期/用户删除、未来检索隔离、UTF-8字节教学token预算与有损历史压缩。没有真实个人画像、LLM摘要、向量检索、身份认证或完整副本删除。能说明这些限制，并独立复现失败Case，才算完成。

[[示例工程/README|代码导航]] · [[参考工程验证记录|作者记录]] · [[../../00 从这里开始|学习首页]]。个人练习保持由自己记录，不自动勾选。

下一单元规划：规划工作流与重新规划，待编写。
""",
    )

if __name__ == "__main__":
    write(
        "示例工程/README.md",
        r"""
## 先运行

VS Code打开本目录，选择工作区根共享解释器：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py
```

仅标准库；用户、时间、确认及聊天全部合成，不调用LLM、不联网、不读取真实个人资料。每次临时SQLite自动关闭清理，不创建单元.venv。完整步骤见 [[../00 记忆与上下文管理学习地图|学习地图]]。

## 代码导航

- [memory.py](./memory.py)：偏好白名单、模拟确认、UTC时间、来源/置信标签、事务版本、到期检索、按用户删除与资源关闭。
- [context.py](./context.py)：UTF-8字节教学Tokenizer、固定结构/当前问题预算、有损goal摘要、成对历史移除与遗漏报告。
- [demo.py](./demo.py)：故意误记→复核纠正、隔离、预算压缩、过期与删除演练。
- [confirmations.json](./fixtures/confirmations.json)：模拟原始确认与期望值，明确不是现实同意。
- [test_memory.py](./tests/test_memory.py)：命中/失败边界、并发版本、删除/隔离、连接关闭、预算/来源与当前问题保护。
- [requirements.txt](./requirements.txt)：标准库说明，测试工具在已有共享环境。

## 验证命令与预期

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

演示created1、unchanged1、updated2，误记Chinese纠正English；24条合成历史带偏好时输入2663→592，输入上限640；删除alice后无命中/事件，bob保留。作者验证见 [[../参考工程验证记录|验证记录]]，不代表学习者完成。

owner需真实应用提供可信身份，本API自身不认证。TTL仅筛掉过期记录；delete删除当前表与事件，不保证擦除备份/源对话/已生成报告。记忆字段作为数据组织，不构成LLM提示注入防护证明。真实模型需匹配Tokenizer及最终聊天模板；本字节预算不等于任何LLM token计量。
""",
        "记忆与上下文示例工程代码导航",
    )

if __name__ == "__main__":
    print("已写入单元28六讲、地图与代码导航")
