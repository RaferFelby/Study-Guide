---
title: 第 3 讲：用 Git 保存可理解的历史
aliases:
  - Linux Git Docker 03
  - Git 分支与合并
tags:
  - curriculum
  - git
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：用 Git 保存可理解的历史

> [!nav] 页面导航
> [[01_学习指南/03_Linux_Git_Docker/00 Linux Git Docker 学习地图#学习顺序|单元 03：Linux Git Docker]] · [[01_学习指南/03_Linux_Git_Docker/逐讲学习/02 用 SSH、rsync 和 tmux 维护远程任务|上一讲]] · [[01_学习指南/03_Linux_Git_Docker/逐讲学习/04 处理冲突并安全撤销|下一讲]]

## 学完后你会做到什么

你会理解工作区、暂存区、提交和分支的关系，能读懂 `status`、`diff`、`log`，创建分支并合并一个小改动。Git 不是网盘，也不是自动替你判断代码好坏的工具；它保存的是你明确记录的版本快照。

## 1. Git 保存了什么

可以把一次提交先理解成“项目在某一时刻的快照 + 作者说明”。Git 通常涉及三个位置：

```text
工作区 → 暂存区 → 提交历史
你正在改的文件   下一次要保存的内容   已命名的版本快照
```

`git add` 把改动放入暂存区；`git commit` 把暂存区内容保存成提交。文件改了但没有 `add`，下一次提交不会自动包含它。这个两步设计让你可以把一部分相关改动组成一个清晰提交。

## 2. 第一次查看仓库

在工作区根目录运行：

```bash
git status
git log --oneline --decorate --all -5
```

`status` 显示当前分支和未提交改动；`log --oneline` 用一行显示历史，`--decorate` 显示分支和标签。当前仓库若尚未有首次提交，`log` 没有历史是正常的。

查看文件具体改动：

```bash
git diff
git diff -- .gitignore
```

`git diff` 默认比较工作区与暂存区；加入暂存区后用 `git diff --cached` 查看“下一次提交将包含什么”。提交前至少看一次 `git diff --cached`。

## 3. 创建一个清晰提交

如果确认当前文件都属于本次初始化，可以按顺序运行：

```bash
git add .
git status
git diff --cached --stat
git commit -m "初始化 AI Agent 算法学习教材"
```

`git add .` 会把当前目录下未忽略文件放入暂存区，所以必须在提交前检查状态；`--stat` 只看文件统计，想看完整内容用 `git diff --cached`。提交信息用动词说明这次保存了什么，不要写毫无信息的 `update`。

PowerShell 使用同样的 Git 命令。Git 身份未配置时会提示设置：

```powershell
git config user.name "你的名字"
git config user.email "你的邮箱"
```

项目级身份只影响当前仓库；不想公开真实邮箱时，可按代码托管平台提供的隐私邮箱设置。

## 4. 分支是什么

分支是指向某个提交的可移动名字。创建分支不会复制整个项目文件夹，而是让你在独立的提交线上开发：

```bash
git switch -c docs/lesson-update
# 修改文件后
git add path/to/file.md
git commit -m "补充一讲教程"
git switch main
```

`switch -c` 创建并切换到新分支；回到 `main` 后，主分支仍停在原来的提交。分支的价值是隔离未完成工作，便于审阅和合并。

## 5. merge：把一条分支合回当前分支

在 `main` 上运行：

```bash
git merge docs/lesson-update
```

Git 会尝试把两个分支的历史合在一起。如果改动互不冲突，可能自动完成；如果两个分支修改同一位置，就进入冲突处理，下一讲会专门练习。合并前确认当前分支是接收改动的分支，用 `git branch --show-current` 检查。

## 6. Git 记录和文件删除

```bash
git log --oneline --all --graph
git show --stat HEAD
git restore --staged path/to/file.md
git restore path/to/file.md
```

`log --graph` 显示分支关系；`show` 查看一个提交；`restore --staged` 只把文件移出暂存区，不丢弃工作区内容；不带 `--staged` 的 `restore` 会丢弃未提交修改，应在确认后使用。

不要把 `restore` 当成撤销历史的万能命令。它只能处理当前工作区或暂存区；已经提交的内容要用 `revert`、`reset` 或新提交处理，边界见下一讲。

## 7. 动手操作

1. 运行 `git status`，记录当前分支和未跟踪目录。
2. 只修改一个练习文件，查看 `git diff`。
3. `git add` 后查看 `git diff --cached`，确认暂存内容。
4. 创建 `practice/git-branch` 分支，提交一个小改动，再切回 `main` 比较文件状态。
5. 在练习分支合并回 `main` 前，先用 `git log --oneline --graph --all` 预测历史形状。

## 8. 常见错误

- **把未跟踪文件当成已保存：** 文件存在不等于进入提交历史。
- **不看 diff 就 `git add .`：** 可能把缓存、临时输出或不相关改动放入提交。
- **在错误分支上提交：** 提交前运行 `git branch --show-current`。
- **把分支当成备份：** 分支仍在同一个仓库，重要数据要有额外备份。

## 9. 练习与答案解析

**跟做：** 创建分支、修改一个 Markdown 文件、查看 diff、提交并切回 `main`。

**独立：** 让两个分支分别修改不同文件，合并后用 `git log --graph` 解释历史。

**迁移：** 为一次“添加 Dockerfile”的工作设计两个提交：一个只添加 Dockerfile，一个补充 README；说明为什么拆开更容易审阅。

> [!example]- 参考思路（先完成再展开）
> 每个提交应表达一个可解释的状态。分支用于隔离进行中的工作；`status` 看范围，`diff` 看内容，`diff --cached` 看提交候选，`log --graph` 看历史。合并前确认目标分支和工作区干净。

完成标准：能解释工作区/暂存区/提交的差异，能创建分支并合并，能在提交前检查实际内容。

## 本讲小结

Git 的核心不是命令数量，而是让每次改动有清晰边界和可追溯历史。下一讲处理多人或多分支改同一文件时的冲突、rebase、reset、revert 和 stash。

## 继续学习

> [!next] 下一步
> [[01_学习指南/03_Linux_Git_Docker/逐讲学习/04 处理冲突并安全撤销|下一讲：处理冲突并安全撤销]]

> [!info]- 练习与记录
> [[01_学习指南/03_Linux_Git_Docker/示例工程/README#代码导航（VS Code）|查看源码]] · [[01_学习指南/03_Linux_Git_Docker/示例工程/README#本地运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 03：Linux、Git、Docker 与远程开发|本单元完成清单]]
