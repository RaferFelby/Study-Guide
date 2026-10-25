---
title: 单元 03 参考工程验证记录
aliases:
  - Linux Git Docker 验证记录
tags:
  - verification
  - linux
  - git
  - docker
status: verified
updated: 2026-09-24
cssclasses: ["guide-page", "guide-reference"]
---

# 单元 03 参考工程验证记录

> [!tip] 导航
> [[01_学习指南/03_Linux_Git_Docker/00 Linux Git Docker 学习地图|单元学习地图]] · [[01_学习指南/03_Linux_Git_Docker/示例工程/README|示例工程代码导航]] · [[00 从这里开始|学习首页]]

这页记录作者对单元 03 示例工程和教材命令的验证范围。它说明参考实现曾被检查，不代替学习者自己的操作记录。

## 验证范围

- Python 标准库服务源码可以编译并通过 unittest。
- Dockerfile、.dockerignore 和 compose.yaml 的内容与教程一致。
- Git、Shell 和远程命令按概念与参数边界审阅。
- Docker 构建与启动需要本机 Docker Engine；若当前环境没有 Docker，只记录未运行，不把未运行写成通过。

## 本机共享环境复验（2026-09-26）

- Windows、Python 3.13.12、仓库根目录 .venv。
- unittest 2 项通过，源码编译检查通过。
- 此复验覆盖本机 Python 示例；Docker Engine 的镜像构建与容器运行仍未验证。

## 作者侧检查命令
- 实际结果：Python unittest 2 项通过，源码编译检查通过。
- Docker CLI 可用，但当前 Docker Engine 未启动，因此镜像构建和容器启动尚未执行。

在示例工程目录运行：

~~~powershell
python -m unittest discover -s tests -v
python -m app.server --host 127.0.0.1 --port 8000
docker build -t linux-git-docker-demo:local .
docker run --rm -p 8000:8000 --memory=256m --cpus=1 linux-git-docker-demo:local
~~~

预期 unittest 为 2 项通过；服务启动后访问 /health 应返回 status 为 ok 的 JSON。Docker 命令的输出、镜像 ID、容器 ID 和日志时间会因环境不同而变化。

## 安全边界

- 示例服务以普通用户运行，不把 token、密码或私钥写入 Dockerfile、镜像或 compose.yaml。
- .dockerignore 排除 Git 元数据、虚拟环境、缓存、测试和实验结果。
- 资源限制是运行上限，不是完整安全隔离；生产部署仍需补丁、权限、网络和密钥管理。
- SSH、rsync、tmux 命令使用假主机名，未连接未知远程服务器。

