---
title: Linux、Git、Docker 与远程开发示例工程
tags:
  - linux
  - git
  - docker
status: verified
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# Linux、Git、Docker 与远程开发示例工程

> [!nav] 页面导航
> [[01_学习指南/03_Linux_Git_Docker/00 Linux Git Docker 学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/03_Linux_Git_Docker/逐讲学习/01 用 Shell 找文件和看日志|从第一讲开始：用 Shell 找文件和看日志]]


这是一个只使用 Python 标准库的最小 HTTP 服务。它的重点不是写一个复杂网站，而是提供一个可以在本地、Docker 容器和远程终端中重复启动的对象，方便练习日志、进程、Git 和容器命令。

## 本地运行

在本目录打开 VS Code 终端。所有本机 Python 示例共用根目录环境：

```powershell
..\..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
..\..\..\.venv\Scripts\python.exe -m app.server --host 127.0.0.1 --port 8000
```

第二条命令会持续运行服务。另开一个终端访问：

```powershell
curl http://127.0.0.1:8000/health
```

预期得到包含 `"status": "ok"` 的 JSON。停止服务时回到运行它的终端按 `Ctrl+C`；不要直接关闭整个编辑器窗口来结束进程。

## Docker 运行

确认 Docker Desktop 或 Docker Engine 已启动后：

```powershell
docker build -t linux-git-docker-demo:local .
docker run --rm --name linux-git-docker-demo -p 8000:8000 --memory=256m --cpus=1 linux-git-docker-demo:local
```

另开终端访问同一个 `/health` 地址。`--rm` 表示容器停止后自动删除；`--memory` 和 `--cpus` 是资源上限，不是让程序自动变快的开关。需要更严格的只读运行时，可参考 [[01_学习指南/03_Linux_Git_Docker/逐讲学习/06 限制资源并安全启动服务|第 6 讲：限制资源并安全启动服务]] 的命令。

> [!note] 从 `docker run` 切换到 Compose
> `docker run` 会持续占用当前终端和宿主机的 8000 端口。要继续练习 Compose，请先回到运行 `docker run` 的终端按 `Ctrl+C` 停止服务，再启动 Compose；否则两个服务会争用同一个端口。

也可以用 Compose 启动服务。先确认 `compose.yaml` 中的配置，再在本目录的终端分步操作。

### 步骤一：构建并在后台启动

```powershell
docker compose up --build -d
```

`-d` 表示让容器在后台运行，终端会返回提示符，方便继续检查。

### 步骤二：查看状态、日志和健康接口

```powershell
docker compose ps
docker compose logs demo
curl http://127.0.0.1:8000/health
```

健康接口应返回包含 `"status": "ok"` 的 JSON。检查完成后再停止服务：

### 步骤三：停止并清理

```powershell
docker compose down
```

## 代码导航（VS Code）

1. [server.py](./app/server.py)：健康检查、JSON 响应、端口参数和进程入口。
2. [test_server.py](./tests/test_server.py)：不启动网络服务的快速单元测试。
3. [Dockerfile](./Dockerfile)：基础镜像、工作目录、非 root 用户、健康检查和启动命令。
4. [.dockerignore](./.dockerignore)：不把虚拟环境、Git 元数据和测试缓存送入构建上下文。
5. [compose.yaml](./compose.yaml)：本地编排、端口、资源限制和只读根文件系统。

## 安全与限制

- 示例不读取真实密钥，也不把 token 写进 Dockerfile、镜像层或 compose 文件。
- 示例服务没有认证、TLS、数据库和生产级日志轮转，不能直接暴露到公网。
- Docker 命令只有在 Docker 引擎可用时才能运行；Shell、Git 和 Python 练习不依赖 Docker。
- Windows PowerShell 与 Linux Shell 的命令选项并不完全相同；教程会说明可移植部分和平台差异。
