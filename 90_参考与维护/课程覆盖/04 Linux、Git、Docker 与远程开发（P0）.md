---
title: 模块 04 覆盖与验收
tags: [reference, coverage]
updated: 2026-10-24
cssclasses: ["guide-page", "guide-reference"]
---

# 模块 04 覆盖与验收

> [!nav] 页面导航
> [[90_参考与维护/01 课程覆盖索引|覆盖索引]]

## 模块 04：Linux、Git、Docker 与远程开发（P0）

教材状态：已编写；详细教材入口为 [[01_学习指南/03_Linux_Git_Docker/00 Linux Git Docker 学习地图|单元 03 学习地图]]。

**学习内容**

- **K04-01** Shell、管道、日志检索、进程/磁盘/GPU 监控（见 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/01 用 Shell 找文件和看日志|第 1 讲：用 Shell 找文件和看日志]]）；
- **K04-02** SSH、rsync、tmux、远程调试（见 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/02 用 SSH、rsync 和 tmux 维护远程任务|第 2 讲：用 SSH、rsync 和 tmux 维护远程任务]]）；
- **K04-03** Git 分支、冲突、rebase、revert、stash（见 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/03 用 Git 保存可理解的历史|第 3 讲：用 Git 保存可理解的历史]]、[[01_学习指南/03_Linux_Git_Docker/逐讲学习/04 处理冲突并安全撤销|第 4 讲：处理冲突并安全撤销]]）；
- **K04-04** Dockerfile、镜像分层、卷、网络、资源限制（见 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/05 读懂 Dockerfile 和镜像|第 5 讲：读懂 Dockerfile 和镜像]]、[[01_学习指南/03_Linux_Git_Docker/逐讲学习/06 限制资源并安全启动服务|第 6 讲：限制资源并安全启动服务]]）。

**验收标准**

- [ ] **C04-01** 能在远程服务器中持久化运行训练任务并恢复现场（见 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/02 用 SSH、rsync 和 tmux 维护远程任务|第 2 讲：用 SSH、rsync 和 tmux 维护远程任务]]）；
- [ ] **C04-02** 能从日志、GPU 利用率和进程状态定位一次性能问题（见 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/01 用 Shell 找文件和看日志|第 1 讲：用 Shell 找文件和看日志]]）；
- [ ] **C04-03** 能解释 merge、rebase、reset 和 revert 的适用边界（见 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/03 用 Git 保存可理解的历史|第 3 讲：用 Git 保存可理解的历史]]、[[01_学习指南/03_Linux_Git_Docker/逐讲学习/04 处理冲突并安全撤销|第 4 讲：处理冲突并安全撤销]]）；
- [ ] **C04-04** 项目可通过 Docker 在干净环境启动，且不把密钥打进镜像（见 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/05 读懂 Dockerfile 和镜像|第 5 讲：读懂 Dockerfile 和镜像]]、[[01_学习指南/03_Linux_Git_Docker/逐讲学习/06 限制资源并安全启动服务|第 6 讲：限制资源并安全启动服务]]）。


## 单元 03 原地图对照：对应总清单

| 原知识编号 | 本单元对应章节 | 形成的理解 |
|---|---|---|
| K04-01 | [[01_学习指南/03_Linux_Git_Docker/逐讲学习/01 用 Shell 找文件和看日志\|第 1 讲：用 Shell 找文件和看日志]] | Shell、管道、日志检索、进程、磁盘和 GPU 观察方法 |
| K04-02 | [[01_学习指南/03_Linux_Git_Docker/逐讲学习/02 用 SSH、rsync 和 tmux 维护远程任务\|第 2 讲：用 SSH、rsync 和 tmux 维护远程任务]] | SSH、rsync、tmux 和远程调试的安全边界 |
| K04-03 | [[01_学习指南/03_Linux_Git_Docker/逐讲学习/03 用 Git 保存可理解的历史\|第 3 讲：用 Git 保存可理解的历史]]、[[01_学习指南/03_Linux_Git_Docker/逐讲学习/04 处理冲突并安全撤销\|第 4 讲：处理冲突并安全撤销]] | 分支、冲突、merge、rebase、reset、revert、stash |
| K04-04 | [[01_学习指南/03_Linux_Git_Docker/逐讲学习/05 读懂 Dockerfile 和镜像\|第 5 讲：读懂 Dockerfile 和镜像]]、[[01_学习指南/03_Linux_Git_Docker/逐讲学习/06 限制资源并安全启动服务\|第 6 讲：限制资源并安全启动服务]] | Dockerfile、镜像层、卷、网络、资源限制和密钥边界 |


## 单元 03 原地图对照：验收标准

| 编号 | 作者侧交付内容 | 教材位置 |
|---|---|---|
| C04-01 | 解释如何在远程服务器中持久化运行任务并恢复现场 | 第 2 讲 |
| C04-02 | 用日志、GPU 利用率和进程状态定位性能问题 | 第 1 讲 |
| C04-03 | 解释 merge、rebase、reset 和 revert 的适用边界 | 第 3～4 讲 |
| C04-04 | 用 Docker 在干净环境启动，且密钥不进入镜像 | 第 5～6 讲 |

作者侧验证记录见 [[90_参考与维护/单元验证/03 Linux_Git_Docker验证记录|参考工程验证记录]]。下一单元为“数据结构、算法与编程面试”。
