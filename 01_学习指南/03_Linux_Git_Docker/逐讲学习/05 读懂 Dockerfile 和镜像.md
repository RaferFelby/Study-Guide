---
title: 第 5 讲：读懂 Dockerfile 和镜像
aliases:
  - Linux Git Docker 05
  - Docker 镜像、容器、卷和网络
tags:
  - curriculum
  - docker
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 5 讲：读懂 Dockerfile 和镜像

> [!nav] 页面导航
> [[01_学习指南/03_Linux_Git_Docker/00 Linux Git Docker 学习地图#学习顺序|单元 03：Linux Git Docker]] · [[01_学习指南/03_Linux_Git_Docker/逐讲学习/04 处理冲突并安全撤销|上一讲]] · [[01_学习指南/03_Linux_Git_Docker/逐讲学习/06 限制资源并安全启动服务|下一讲]]

## 学完后你会做到什么

你会区分镜像和容器，能逐行读懂示例 Dockerfile，理解构建上下文、镜像层、端口映射、卷和网络，并能在本地构建和启动一个最小服务。Docker 是环境隔离和分发工具，不会自动修复程序逻辑。

## 1. 镜像与容器是什么

镜像是启动容器所需的只读文件系统和元数据；容器是镜像的一次运行实例，包含进程、网络和可写层。可以把镜像想成“安装好的模板”，容器是“用模板启动的一次运行”；这个类比不意味着容器一定永久保存数据，容器删除后可写层通常也会消失。

先检查 Docker 是否可用：

~~~powershell
docker version
docker info
~~~

如果提示无法连接 daemon，先启动 Docker Desktop 或 Linux Docker Engine。没有 Docker 时仍可阅读 Dockerfile并完成结构练习，不要为了测试随意安装未知脚本。

## 2. 逐行阅读 Dockerfile

示例工程的 Dockerfile 主要步骤是：

~~~dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY app ./app
USER appuser
EXPOSE 8000
HEALTHCHECK ...
CMD ["python", "-m", "app.server", "--host", "0.0.0.0", "--port", "8000"]
~~~

- FROM 选择基础镜像。slim 比完整系统小，但可用工具更少。
- ENV 设置环境变量；这里只关闭字节码文件并让日志立即输出。
- WORKDIR 设置后续命令的工作目录。
- RUN 在构建镜像时执行，创建非 root 用户。
- COPY 把构建上下文中的 app 目录复制到镜像。
- USER 让服务进程以普通用户运行，减少进程被利用后的权限。
- EXPOSE 是文档性声明，不等于自动把端口暴露到宿主机。
- HEALTHCHECK 让 Docker 通过健康地址判断服务是否响应。
- CMD 是容器默认启动命令，运行时可被覆盖。

## 3. 构建上下文与镜像层

在示例工程目录运行：

~~~powershell
docker build -t linux-git-docker-demo:local .
docker image ls linux-git-docker-demo
~~~

最后的点表示“把当前目录作为构建上下文”。Docker 只能读取上下文中的文件，所以 .dockerignore 很重要：它排除 .git、.venv、缓存、测试和结果文件，减少上传内容和泄露风险。

Dockerfile 的每条主要指令会产生可缓存的构建层。把变化频繁的文件复制放在安装稳定依赖之后，通常更容易利用缓存；但层缓存不是安全边界，曾经写入镜像层的密钥不能靠后续删除来消除。

## 4. 启动、观察和停止容器

~~~powershell
docker run --rm --name linux-git-docker-demo -p 8000:8000 linux-git-docker-demo:local
~~~

- --rm 在容器停止后清理容器。
- --name 给运行实例起可读名字。
- -p 把宿主机端口映射到容器端口，格式是宿主机:容器。
- 最后的镜像名决定使用哪一个镜像。

另开终端观察：

~~~powershell
docker ps
docker logs linux-git-docker-demo
docker inspect linux-git-docker-demo
~~~

停止前台容器可按 Ctrl+C；后台运行可加 -d，然后用 docker stop 停止。docker exec 允许进入运行中的容器执行诊断命令，但生产容器应优先依靠日志、健康检查和可重复启动命令，不要把手动改容器当成永久修复。

## 5. 端口、卷和网络

端口映射解决“宿主机如何访问容器服务”；它不等于容器之间已经互相发现。Compose 会为同一项目创建网络，服务通常通过服务名访问。

容器中的写入默认进入容器可写层。需要长期保留的数据应使用卷：

~~~powershell
docker volume create demo-data
docker run --rm -v demo-data:/data python:3.12-slim python -c "from pathlib import Path; Path('/data/example.txt').write_text('saved')"
docker run --rm -v demo-data:/data python:3.12-slim cat /data/example.txt
~~~

卷的生命周期独立于单个容器；删除容器不一定删除卷，但卷也可能包含敏感数据，需要按项目规则管理。示例 HTTP 服务没有持久化需求，所以 Dockerfile 不创建数据卷。

## 6. 不要把密钥写进镜像

下面这些做法都不安全：

~~~dockerfile
ENV API_KEY=real-secret
COPY .env /app/.env
RUN echo "real-secret" > /app/config.txt
~~~

即使后续删除文件，密钥可能仍存在历史镜像层或构建缓存。正确做法取决于部署平台：运行时注入环境变量、使用 Docker secrets 或云平台密钥管理，并限制日志和错误输出。教程示例不需要任何真实密钥。

## 7. 动手操作

1. 阅读 Dockerfile，逐行写出构建阶段与运行阶段发生的事情。
2. 检查 .dockerignore，解释为什么不复制 .venv 和 .git。
3. 若 Docker 可用，构建镜像并启动服务，访问 /health。
4. 查看 docker ps 和 docker logs，停止并确认 --rm 是否删除容器。
5. 修改 app/server.py 的响应文字，重新构建，观察哪些层可以复用。

## 8. 常见错误

- **把 EXPOSE 当成端口映射：** 仍需要 docker run 的 -p。
- **在容器里手动 pip install 后当成修复：** 容器重建后会消失，应修改 Dockerfile。
- **把密钥放进 ENV 或 COPY：** 镜像层和构建日志可能留下痕迹。
- **容器停止后数据不见：** 需要卷或外部存储，不能依赖容器可写层。

## 9. 练习与答案解析

**跟做：** 构建并运行示例服务，用 docker logs 观察启动信息。

**独立：** 解释为什么服务要使用非 root 用户，以及为什么 -p 8000:8000 仍然需要宿主机端口未被占用。

**迁移：** 为一个需要上传文件的服务设计卷挂载方案，列出宿主机目录、容器目录、备份和权限风险。

> [!example]- 参考思路（先完成再展开）
> 镜像描述环境和启动方式，容器是一次运行实例；端口映射只负责访问路径；长期数据用卷；密钥由运行时注入而不是进入 Dockerfile。修改源码后重新 build，不能把容器内临时修改当作版本。

完成标准：能构建并观察一个镜像，能说明容器停止后的数据边界，能指出至少三种把密钥打进镜像的风险。

## 本讲小结

Dockerfile 是构建说明，镜像是可分发模板，容器是运行实例；端口、卷和网络解决不同问题。下一讲加入资源限制、只读文件系统、Compose 和一次完整的安全启动流程。

## 继续学习

> [!next] 下一步
> [[01_学习指南/03_Linux_Git_Docker/逐讲学习/06 限制资源并安全启动服务|下一讲：限制资源并安全启动服务]]

> [!info]- 练习与记录
> [[01_学习指南/03_Linux_Git_Docker/示例工程/README#代码导航（VS Code）|查看源码]] · [[01_学习指南/03_Linux_Git_Docker/示例工程/README#本地运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 03：Linux、Git、Docker 与远程开发|本单元完成清单]]
