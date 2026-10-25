---
title: 第 2 讲：用 SSH、rsync 和 tmux 维护远程任务
aliases:
  - Linux Git Docker 02
  - SSH、rsync、tmux 与远程调试
tags:
  - curriculum
  - linux
  - ssh
  - remote
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：用 SSH、rsync 和 tmux 维护远程任务

> [!nav] 页面导航
> [[01_学习指南/03_Linux_Git_Docker/00 Linux Git Docker 学习地图#学习顺序|单元 03：Linux Git Docker]] · [[01_学习指南/03_Linux_Git_Docker/逐讲学习/01 用 Shell 找文件和看日志|上一讲]] · [[01_学习指南/03_Linux_Git_Docker/逐讲学习/03 用 Git 保存可理解的历史|下一讲]]

## 学完后你会做到什么

你会理解 SSH 客户端、远程主机、密钥和端口转发；能用 rsync 或 scp 同步代码；能用 tmux 让训练任务在网络断开后继续，并知道如何恢复现场。所有命令都以“先确认目标、再执行同步”为前提。

## 1. SSH 是什么

SSH 是加密的远程登录协议。你在本机输入命令，命令在远程 Linux 主机执行；终端显示的是远程输出。它不是把远程文件夹自动变成本地文件夹，也不是网络加速器。

最小连接形式：

```bash
ssh username@server.example.com
```

第一次连接时，SSH 会显示主机指纹并询问是否信任。应通过管理员或可信渠道核对指纹，不能为了方便对任何陌生指纹输入 `yes`。核对成功后，主机记录写入 `~/.ssh/known_hosts`。

## 2. 用密钥代替反复输入密码

在本机生成一对密钥：

```bash
ssh-keygen -t ed25519 -C "your-name@your-device"
```

私钥留在本机，公钥复制到远程账号。私钥像房门钥匙，不能上传到 Git、Docker 镜像或聊天记录；公钥可以放在远程账号的 `~/.ssh/authorized_keys` 中。

Linux/macOS 常用复制命令：

```bash
ssh-copy-id username@server.example.com
```

Windows OpenSSH 环境没有 `ssh-copy-id` 时，可以让管理员把 `.pub` 文件中的一整行追加到远程 `authorized_keys`，并确保远程目录权限正确。不要把私钥内容复制过去。

为了少写主机参数，可以编辑本机 `~/.ssh/config`：

```sshconfig
Host my-lab
    HostName server.example.com
    User username
    IdentityFile ~/.ssh/id_ed25519
    Port 22
```

之后运行 `ssh my-lab`。配置文件只保存主机连接信息，不保存密码或私钥内容。

## 3. 安全地同步代码

`rsync` 可以只传输变化的文件，并保留目录结构：

```bash
rsync -av --dry-run --exclude '.venv/' --exclude '__pycache__/' \
  ./ username@server.example.com:~/projects/demo/
```

`-a` 保留常见文件属性并递归目录；`-v` 显示过程；`--dry-run` 只预览不实际传输。第一次同步必须先看 dry-run 输出，确认目标目录和排除项正确，再去掉 `--dry-run`。

Windows 或没有 rsync 时可使用：

```powershell
scp -r .\app username@server.example.com:~/projects/demo/
```

`scp -r` 适合简单复制，但不会像 rsync 一样只传变化部分。不要把 `.venv`、模型缓存、日志和密钥目录一并上传；远程环境应根据依赖清单重新安装。

## 4. tmux 让任务跨越断线

普通 SSH 会话关闭后，前台命令可能收到挂断信号。tmux 提供一个远程终端会话，SSH 只是连接它的窗口。先在远程机器进入工程根目录，按该项目的依赖说明准备并激活远程 Python 环境，然后运行 `python --version` 确认当前解释器；不要把 Windows 本机的 `.venv` 复制到 Linux。下面的 `mkdir -p logs` 会创建日志目录，目录已存在时也可以安全重复运行：

```bash
tmux new -s train
set -o pipefail
mkdir -p logs
python -u train.py --config configs/demo.yaml 2>&1 | tee logs/train.log
```

这里使用 Bash 的 `set -o pipefail`，这样 Python 训练失败时，整条管道也会返回失败状态；否则 `tee` 成功写入日志可能掩盖训练程序的失败退出码。`python -u` 让输出尽量及时写到终端和日志，避免训练日志因缓冲而延迟出现。实际项目还要检查训练程序自己的错误处理和退出码。

按 `Ctrl+B`，松开后按 `D`，可以 detach（离开会话但不停止任务）。重新 SSH 登录后：

```bash
tmux ls
tmux attach -t train
```

如果不记得会话名称，先 `tmux ls`；不要随意创建很多同名会话。训练命令同时写入日志，恢复时先看屏幕，再用 `tail -f logs/train.log` 查看完整记录。

## 5. 端口转发与远程调试

远程服务监听 `127.0.0.1:8000` 时，外部通常不能直接访问。SSH 本地端口转发把本机端口连接到远程端口：

```bash
ssh -L 8000:127.0.0.1:8000 my-lab
```

保持这个 SSH 会话打开，在本机浏览器访问 `http://127.0.0.1:8000`，请求会经加密通道到远程服务。 `-L` 的格式是“本地端口:远程目标地址:远程端口”。不要把服务改成 `0.0.0.0` 并开放防火墙作为第一选择。

调试器也可以使用端口转发，但要限制监听地址、确认端口和用户，避免把调试接口暴露给公网。远程调试前记录代码提交号、Python 版本、启动命令和配置路径。

## 6. 断线后的恢复现场

一个可复现的恢复流程是：

1. `ssh my-lab` 重新连接。
2. `tmux ls` 确认会话是否还在。
3. `tmux attach -t train` 恢复屏幕。
4. 用 `ps`、日志尾部和输出目录确认任务是否继续或已经结束。
5. 若任务退出，先保存退出码、最后错误和提交号，再决定是否重启。

不要看到窗口消失就直接重新启动同一训练，可能造成两个进程同时写同一 checkpoint。先确认旧进程和输出目录状态。

## 7. 动手操作

没有远程服务器时，在本机完成安全演练：

1. 运行 `ssh-keygen` 前先确认本机已有的 `~/.ssh` 文件，不覆盖旧私钥。
2. 阅读并修改示例 `~/.ssh/config`，主机名使用假值，不要连接未知地址。
3. 用 `rsync --dry-run` 或 `scp` 命令解释哪些文件应排除。
4. 如果本机有 tmux，在会话中运行示例测试，detach 后重新 attach。
5. 写出一条“断线后恢复训练”的步骤清单。

## 8. 常见错误

- **把私钥上传到服务器或仓库：** 私钥只应留在需要发起连接的本机。
- **没有 dry-run 就使用 rsync：** 目标路径和末尾 `/` 可能造成目录层级不同，先预览。
- **断线后重复启动：** 先用进程、tmux 和日志确认原任务状态。
- **开放调试端口到公网：** 优先用 SSH 本地转发和访问控制。

## 9. 练习与答案解析

**跟做：** 在本地 tmux 中运行一个会持续打印数字的 Python 命令，detach 后 attach，确认进程没有因离开会话停止。

**独立：** 写一条 rsync dry-run 命令，把 `app/` 同步到远程 `~/projects/demo/`，排除 `.venv` 和缓存，并解释每个参数。

**迁移：** 为远程 TensorBoard 或 Jupyter 设计 SSH 端口转发命令，说明为什么不直接开放公网端口。

> [!example]- 参考思路（先完成再展开）
> 远程任务需要“tmux 会话 + 日志文件 + 提交号 + 配置路径”。同步前用 `--dry-run`，同步后在远程用 `git rev-parse --short HEAD` 和 `python --version` 记录环境。端口转发让服务仍只监听远程本机，访问者必须拥有 SSH 权限。

完成标准：能解释私钥和公钥的区别，能安全预览同步内容，能 detach/attach tmux，并能写出断线恢复顺序。

## 本讲小结

SSH 负责安全连接，rsync/scp 负责文件传输，tmux 负责让任务脱离当前终端继续运行。下一讲开始学习 Git 如何保存可理解的项目历史。

## 继续学习

> [!next] 下一步
> [[01_学习指南/03_Linux_Git_Docker/逐讲学习/03 用 Git 保存可理解的历史|下一讲：用 Git 保存可理解的历史]]

> [!info]- 练习与记录
> [[01_学习指南/03_Linux_Git_Docker/示例工程/README#代码导航（VS Code）|查看源码]] · [[01_学习指南/03_Linux_Git_Docker/示例工程/README#本地运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 03：Linux、Git、Docker 与远程开发|本单元完成清单]]
