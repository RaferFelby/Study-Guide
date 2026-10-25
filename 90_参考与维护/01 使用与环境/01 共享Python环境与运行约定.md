---
title: 共享 Python 环境与运行约定
tags: [reference, environment]
updated: 2026-10-24
cssclasses: ["guide-page", "guide-reference"]
---

# 共享 Python 环境与运行约定

> [!nav] 页面导航
> [[90_参考与维护/00 参考与维护导航|参考与维护]]

## 共享 Python 环境

扩展单元 39 的默认运行仅用标准库，真实模型接口为选做操作教程；单元 40 使用已有 PyTorch 的 CPU 路径。不新增虚拟环境或安装依赖。

单元 14～25、27～32 的运行示例均使用标准库。单元 26、33～38 使用共享环境中已有的 PyTorch，包含 CPU 与 CUDA 路径；单元 35 的公开归档评分本身只使用标准库，PyTorch 用于实际权重重评，单元 36 还包含本机双 CPU 进程 Gloo/DDP。单元 38 的独立 C++ 程序使用已有 GCC，原生 CUDA 编译使用 nvcc 和获批安装的 MSVC／Windows SDK，不增加 Python 包。单元 09 的架构估算器、单元 10 的 tokenizer/样本构造示例、单元 11 的本机 HTTP 假服务和单元 12 的 RAG 数据工程示例只使用 Python 标准库，不增加依赖。

所有本机单元统一使用仓库根目录的 `.venv`。共享环境的开发依赖见 [requirements-dev.txt](../../requirements-dev.txt)；机器学习单元使用的依赖约束见 [requirements-ml.txt](../../requirements-ml.txt)，不要在单元目录另建虚拟环境。

当前工作区已经有共享环境，先用`.\.venv\Scripts\python.exe -m pip check`和相关包的导入检查确认现状。下面创建与安装命令只用于首次准备尚无环境的工作区；创建前核对版本兼容性，安装或升级依赖须先获得明确批准。不要对已有环境重复执行升级命令。

首次准备获批后，在仓库根目录的 PowerShell 终端运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

单元 06、08 需要 PyTorch。安装前按设备选择一种后端：

CPU与CUDA wheel提供同一套核心PyTorch接口，设备放置和部分设备功能不同。CUDA运行需要可用NVIDIA GPU与支持该运行时的驱动；单纯使用已安装wheel进行训练通常不要求本机nvcc。编译本单元38的原生CUDA才另需Toolkit与兼容宿主编译器。驱动、wheel运行时和Toolkit版本号不要求字符串完全相同，应检查支持关系；本机torch运行时13.0、Toolkit13.2已分别验证，不能拿此组合推断任意版本都兼容。

```powershell
# CPU
.\.venv\Scripts\python.exe -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu

# NVIDIA CUDA 13.0
.\.venv\Scripts\python.exe -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cu130
```

然后安装所有单元共用的 NumPy、测试和开发工具：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

单元 07 需要 pandas 与 scikit-learn；单元 13 的 LSA 检索复用 scikit-learn。确认工作区依赖安装已获批准后，在仓库根目录安装 [requirements-ml.txt](../../requirements-ml.txt)；它会按清单安装 CPU 数据科学包及其传递依赖，不需要选择 CUDA。

运行命令前进入相应单元的“示例工程”目录，再使用 `..\..\..\.venv\Scripts\python.exe`。需要导入单元 01 的 `ticketkit` 或单元 02 的 `reprokit` 时，按该工程 README 将当前源码以可编辑方式安装到共享环境；不要同时安装另一份同名工程包。

在 VS Code 中把 Python 解释器选择为仓库根目录的 `.venv\Scripts\python.exe`。安装后可运行 `..\..\..\.venv\Scripts\python.exe -m pip check`（在单元示例工程目录内）检查依赖是否冲突。

本机已验证的 CUDA 环境精确版本见 [requirements-lock-cu130.txt](../../requirements-lock-cu130.txt)。它适用于 Windows、Python 3.13.12 和 CUDA 13.0 wheel；CPU 或其他平台应按各自后端重新生成锁定文件，不能直接套用此文件。
