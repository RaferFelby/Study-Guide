---
title: 第 2 讲：用 Schema 拦住错误参数
tags: [tools, schema, validation]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：用 Schema 拦住错误参数

> [!nav] 页面导航
> [[01_学习指南/15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图#学习顺序|单元 15：工具调用协议与工具设计]] · [[01_学习指南/15_工具调用协议与工具设计/逐讲学习/01 为一个只读工具写清输入输出|上一讲]] · [[01_学习指南/15_工具调用协议与工具设计/逐讲学习/03 关联工具调用与结果回传|下一讲]]

## 要解决什么问题

模型可能给top_k="3"、漏query、添加role=staff，甚至给无效JSON。执行器必须在真正查询/写入前拦住这些错误。**Schema**描述数据结构约束；它不验证业务权限，也不保证参数含义正确。

检查分三层：文本是否合法JSON → 结构/类型/范围是否符合契约 → 当前身份与业务前提是否允许执行。别用“模型支持结构化输出”跳过服务端校验。

前置为字典/set、异常与JSON。JSON Schema的标准定义见[对象字段与必填项](https://json-schema.org/understanding-json-schema/reference/object)；本示例只实现实际用到的扁平子集，不冒充完整标准验证器。

## 把约束读成中文

search_policies参数：

```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string", "minLength": 1, "maxLength": 200},
    "top_k": {"type": "integer", "minimum": 1, "maximum": 5}
  },
  "required": ["query", "top_k"],
  "additionalProperties": false
}
```

type=object要求对象；properties说明每个允许字段；required列必须提供的字段；additionalProperties=false拒绝其他键。只有properties没有required时，字段不自动必填。这是初学者常见误解。

query长度限制是字符数；整个参数JSON还有8192字节上限，中文UTF-8一个字符可能占多个字节。两种单位不能混用。本工程额外拒绝只含空白的字符串，这是业务约束，比minLength=1严格；标准Schema字符串长度本身不会自动去空白。

top_k必须是整数且1～5。Python中bool是int子类，`isinstance(True,int)`为True，所以工程用 `type(value) is int`避免把true当1。这是Python实现边界，不代表JSON布尔等于JSON整数。

## 先解析再校验

在示例工程新建 `inspect_validation.py`：

```python
from contracts import TOOL_SCHEMAS, parse_arguments, validate_arguments

arguments = parse_arguments('{"query":"storage","top_k":1}')
validate_arguments(arguments, TOOL_SCHEMAS["search_policies"]["parameters"])
print("参数合法：", arguments)
```

预期合法字典。把1换成true，parse成功（true变Python True），validate抛ValueError；把字符串末尾括号删去，parse就抛JSON解析错误。这两种阶段不同，应记录但对外可统一invalid_arguments。

`validate_arguments`先算缺少和额外字段，再逐项检查类型及长度/范围。这里缺少任何required都会拒绝，不采用未说明的默认值。若工具采用默认top_k，应同时修改Schema、执行器和教程，不能仅在一边偷偷补值。

## 重复键、非有限数与超长输入

JSON文本 `{"query":"public","query":"private"}` 中同键出现两次，不同解析器可能保留不同项，易造成前后校验不一致。示例用object_pairs_hook逐对检查，重复键拒绝。

Python json默认可接受NaN/Infinity等非标准数值；工程parse_constant拒绝它们。超长输入先按UTF-8字节拦截，避免对任意长数据无界解析。深度过大仍可能RecursionError，执行边界转换为稳定参数错误。

[Python JSON文档](https://docs.python.org/3.13/library/json.html)说明这些默认行为；生产校验还需要规范版本、嵌套深度、编码、总请求大小和成熟Schema库。不要把手写子集逐渐扩成难以验证的通用库。

## Schema管不到什么

合法query="database retention"不能授权public看内部政策；合法title="创建工单"不能表示用户已经同意写入；合法幂等键也不能保证数据库原子性。参数还可能语义错误：top_k=1合法，但用户要两条时仍没遵守需求。

工具选择/参数语义评估见第6讲，权限与批准见第4讲。不同责任分开，排错时才知道改哪里。

## 常见错误与练习

把"1"强制转1：可能掩盖协议错误，除非契约明确允许转换；本工程拒绝。允许额外role字段但执行器忽略：容易误导模型，以为可控授权。maxLength按字节实现：与字符标准不同，需命名清楚。

**跟做：** 测试缺query、top_k=true、top_k=6、额外role四种输入，预测在哪层失败。

**独立：** 给create_ticket标题和幂等键设计边界题：空串、空白、最大长度、超过最大长度。完成标准：能解释字符数与字节数不同。

**迁移：** 用成熟JSON Schema库替代子集校验前，写兼容清单：草案版本、支持字段、非空白业务规则、错误映射和失败测试。先准备方案，需要新增包时按工作区规则申请，不直接安装。

> [!example]- 参考答案与解析
> 四种都能解析成JSON对象，但validate分别在required、类型、范围、额外字段失败。标题长度80可通过，81拒绝；空白即使长度1也被业务规则拒绝。JSON字节总量另有上限，中文字符与ASCII字节不同。结构合法仍要检查语义、权限和副作用。

## 继续学习

> [!next] 下一步
> [[01_学习指南/15_工具调用协议与工具设计/逐讲学习/03 关联工具调用与结果回传|下一讲：关联工具调用与结果回传]]

> [!info]- 练习与记录
> [[01_学习指南/15_工具调用协议与工具设计/示例工程/README#代码导航|查看源码]] · [[01_学习指南/15_工具调用协议与工具设计/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 15：工具调用协议与工具设计|本单元完成清单]]
