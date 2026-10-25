---
title: 第 1 讲：用 Shell 找文件和看日志
aliases:
  - Linux Git Docker 01
  - Shell、日志、进程和磁盘
tags:
  - curriculum
  - linux
  - shell
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：用 Shell 找文件和看日志

> [!nav] 页面导航
> [[01_学习指南/03_Linux_Git_Docker/00 Linux Git Docker 学习地图#学习顺序|单元 03：Linux Git Docker]] · [[01_学习指南/03_Linux_Git_Docker/逐讲学习/02 用 SSH、rsync 和 tmux 维护远程任务|下一讲]]

## 学完后你会做到什么

你会知道 Shell 是什么，能在 Linux 或 WSL 中查看当前位置、列出文件、筛选日志、观察进程和磁盘；还会知道 GPU 命令应该观察哪些指标。Windows PowerShell 的常用等价写法会同时给出。

本讲的目标不是背命令，而是形成一条排查顺序：先确认“我在哪”，再确认“文件是否存在”，然后看“程序是否在运行”，最后看“资源是否够用”。

> [!contents]- 本讲导航
> - [[#学完后你会做到什么|学完后你会做到什么]]
> - [[#1. Shell、终端和命令|1. Shell、终端和命令]]
> - [[#2. 浏览和操作文件|2. 浏览和操作文件]]
> - [[#3. 管道：让一个命令的输出成为下一个命令的输入|3. 管道：让一个命令的输出成为下一个命令的输入]]
> - [[#4. 查找日志中的关键内容|4. 查找日志中的关键内容]]
> - [[#5. 查看进程和资源|5. 查看进程和资源]]
> - [[#6. 一条可重复的排查顺序|6. 一条可重复的排查顺序]]
> - [[#7. 动手操作|7. 动手操作]]
> - [[#8. 常见错误|8. 常见错误]]
> - [[#9. 练习与答案解析|9. 练习与答案解析]]
> - [[#本讲小结|本讲小结]]

## 1. Shell、终端和命令

终端是输入文字命令、显示输出的窗口；Shell 是解释这些命令的程序，例如 Linux 常见的 Bash。它们不是同一个概念：终端像窗口，Shell 像窗口里负责理解指令的人。

先在 VS Code 中打开本仓库根目录（也就是同时包含 `00 从这里开始.md` 和 `README.md` 的目录），再打开集成终端运行。先确认当前位置和根目录下的内容：

```bash
pwd
ls
```

`pwd` 显示当前目录，`ls` 列出当前目录内容。PowerShell 等价写法是：

```powershell
Get-Location
Get-ChildItem
```

命令的相对路径都从当前目录开始计算，所以排查“文件找不到”时，第一步永远是确认当前目录。

## 2. 浏览和操作文件

```bash
cd 01_学习指南/03_Linux_Git_Docker/示例工程
find . -maxdepth 2 -type f
mkdir -p results
cp README.md results/README.copy.md
mv results/README.copy.md results/README.backup.md
```

`cd` 进入目录；`find` 搜索文件；`mkdir -p` 创建目录并在上级目录不存在时一并创建；`cp` 复制；`mv` 移动或重命名。第一次操作重要文件前，先用 `pwd` 和 `find` 确认目标，不要把通配符 `*` 用在不确定的目录上。

PowerShell 常见写法：

```powershell
Set-Location '01_学习指南/03_Linux_Git_Docker/示例工程'
Get-ChildItem -Recurse -File | Select-Object -First 20
New-Item -ItemType Directory -Force results
Copy-Item README.md results/README.copy.md
Move-Item results/README.copy.md results/README.backup.md
```

路径中的引号用于保护空格或特殊字符。教程中的 Linux 命令不要直接复制到 PowerShell，先看平台对应版本。

## 3. 管道：让一个命令的输出成为下一个命令的输入

管道用 `|` 连接命令。例如：

```bash
find . -type f | sort | head -n 10
```

先找文件，再按文字排序，最后只显示前 10 行。管道传递的是文本流，不是“把所有命令合并成一个程序”；中间某一步输出格式变化，后一步就可能失效。

PowerShell 的管道传递对象，因此可以按属性筛选：

```powershell
Get-ChildItem -Recurse -File | Where-Object Length -gt 1000 | Select-Object FullName, Length
```

这也是两种 Shell 的重要差异：Linux 命令通常处理文本，PowerShell 命令通常处理对象。

## 4. 查找日志中的关键内容

程序日志常包含时间、级别、请求编号和错误原因。Linux 中可以这样筛选：

```bash
rg -n "ERROR|WARNING|timeout" service.log
tail -n 50 service.log
tail -f service.log
```

`rg -n` 搜索并显示行号；`tail -n 50` 显示最后 50 行；`tail -f` 持续跟随新增内容，适合观察正在运行的服务。按 `Ctrl+C` 退出 `tail -f`，不会停止服务本身。

PowerShell 写法：

```powershell
Select-String -Path service.log -Pattern 'ERROR|WARNING|timeout'
Get-Content service.log -Tail 50
Get-Content service.log -Wait
```

不要先把整个巨大日志文件用编辑器打开；先按时间、请求 ID 或错误关键词缩小范围。遇到一条错误时，再向前查看上下文。

## 5. 查看进程和资源

一个程序“很慢”不一定是代码逻辑错，可能是 CPU、内存、磁盘或外部服务等待。Linux 常用：

```bash
ps aux | head
top
df -h
du -sh .
```

`ps` 查看进程快照；`top` 动态观察 CPU 和内存；`df -h` 查看磁盘分区剩余空间；`du -sh .` 查看当前目录占用。 `top` 中要先看进程是否存在，再看 CPU/内存是否异常。

如果机器有 NVIDIA GPU，可运行：

```bash
nvidia-smi
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv
```

重点看 GPU 利用率、显存使用、温度和进程列表。GPU 利用率低不一定说明 GPU 坏了：数据读取、CPU 预处理、网络等待或 batch 太小都可能让 GPU 等待。没有 NVIDIA GPU 时命令不存在是正常情况，不要把它当作程序故障。

## 6. 一条可重复的排查顺序

假设服务返回很慢，先记录：

```text
1. 当前目录与启动命令
2. 进程 ID 和启动时间
3. 最近日志中的请求 ID、错误和超时
4. CPU、内存、磁盘剩余空间
5. 若使用 GPU，再看显存、利用率和温度
```

每次只改变一个排查动作，并保留命令输出。这样别人能复现你的判断，而不是只得到“我感觉是显存不够”。

## 7. 动手操作

1. 在示例工程目录运行 `pwd`/ `Get-Location` 和目录列表命令。
2. 在 Windows PowerShell 中用 `..\..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v *> test.log` 运行测试并保存输出；在 Linux/WSL 中，从示例工程目录运行 `../../../.venv/bin/python -m unittest discover -s tests -v > test.log 2>&1`。两种命令都使用各自运行环境工作区根目录的共享 `.venv`；Windows 的 `.venv` 不能跨到 WSL/Linux 使用。
3. 用 `rg` 或 `Select-String` 搜索 `ok`、`FAIL` 和 `ERROR`。
4. 查看当前目录的磁盘占用；若有 GPU，再记录 `nvidia-smi` 输出。

预期结果：你能说明每条命令从哪里读输入、输出到哪里，以及它对排查哪个问题有帮助。

## 8. 常见错误

- **在错误目录运行命令：** 先 `pwd`/`Get-Location`，再检查相对路径。
- **把 `tail -f` 当成服务进程：** 它只是观察日志，按 `Ctrl+C` 只会退出观察。
- **看到 GPU 利用率低就直接加大 batch：** 先确认瓶颈是数据读取、CPU、网络还是显存。
- **直接删除大日志：** 先保存需要的时间段和请求 ID，再按项目规则轮转或清理。

## 9. 练习与答案解析

**跟做：** 找出示例工程所有 `.py` 文件，并只显示其中包含 `def` 的行。

**独立：** 设计一条命令，从日志中找出最近 20 行含 `timeout` 的记录，并说明 Linux 与 PowerShell 写法。

**迁移：** 假设训练进程 CPU 100%、GPU 利用率 0%、磁盘剩余 1%，写出你的排查顺序和下一条命令。

> [!example]- 参考思路（先完成再展开）
> 文件搜索可用 `rg -n '^\s*def ' --glob '*.py'`；日志先用 `tail`/`Get-Content -Tail` 缩小范围再搜索。训练诊断不能只看 GPU，先确认进程、磁盘和数据读取是否阻塞，再看显存和 GPU 利用率。

完成标准：能在不打开文件管理器的情况下定位文件，能实时观察日志，能说出 CPU、内存、磁盘和 GPU 指标分别帮助排查什么。

## 本讲小结

Shell 是组合小工具的方式；管道让前一步输出成为后一步输入；日志检索和资源观察要结合上下文。下一讲学习如何安全连接远程服务器，并让长任务在断开终端后继续运行。

> [!nav] 路线续读
> 若本讲已到当前路线列出的范围末尾，返回原阶段继续下一项或检查产物；继续单元学习时沿下方“下一讲”。
>
> - [[00_学习路线/05 学习推理系统与GPU工程#阶段 1：准备系统与张量基础|学习推理系统与GPU工程 · 阶段 1：准备系统与张量基础]]

## 继续学习

> [!next] 下一步
> [[01_学习指南/03_Linux_Git_Docker/逐讲学习/02 用 SSH、rsync 和 tmux 维护远程任务|下一讲：用 SSH、rsync 和 tmux 维护远程任务]]

> [!info]- 练习与记录
> [[01_学习指南/03_Linux_Git_Docker/示例工程/README#代码导航（VS Code）|查看源码]] · [[01_学习指南/03_Linux_Git_Docker/示例工程/README#本地运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 03：Linux、Git、Docker 与远程开发|本单元完成清单]]
