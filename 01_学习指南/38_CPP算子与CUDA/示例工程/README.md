---
title: README
tags: [learning, cpp, cuda, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# README

> [!nav] 页面导航
> [[01_学习指南/38_CPP算子与CUDA/00 C++算子与CUDA学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/38_CPP算子与CUDA/逐讲学习/01 编译第一个C++程序并读懂执行过程|从第一讲开始：编译第一个C++程序并读懂执行过程]]

## 从哪里开始

Obsidian读 [[01_学习指南/38_CPP算子与CUDA/00 C++算子与CUDA学习地图|学习地图]]。VS Code在本目录阅读、编译和运行，Python统一根共享环境。

## 代码导航

- [basics.cpp](./basics.cpp)：引用、vector、模板求和和安全越界演示。
- [affine_cpu.cpp](./affine_cpu.cpp)：借用连续float32地址的C接口CPU循环。
- [affine_cuda.cu](./affine_cuda.cu)：原生CUDA核函数、尾部边界和调用方流。
- [build.py](./build.py)：已有GCC构建CPU，已有nvcc和MSVC构建本机GPU目标；不安装工具。
- [operator_impl.py](./operator_impl.py)：ctypes完整参数声明、输入契约、PyTorch注册、fake和输入梯度。
- [probe.py](./probe.py)：先值校验后5次预热、15次中位数同步墙钟对照。
- [test_operator.py](./test_operator.py)：CPU/GPU值、梯度、契约、注册和非默认流。
- [requirements.txt](./requirements.txt)：共享环境已有PyTorch版本，不据此自动安装。

## 环境与运行

实际环境Python3.13.12、PyTorch2.14.0+cu130（运行时13.0）、GCC15.2、nvcc13.2、MSVC v143与Windows SDK。Windows64位，GPU RTX5070 Laptop，构建根据本机能力选择sm目标。Python包未新增或升级。

在本示例工程PowerShell按顺序执行，前一步成功再继续：

```powershell
..\..\..\.venv\Scripts\python.exe build.py --target cpu
..\..\..\.venv\Scripts\python.exe build.py --target cuda
..\..\..\.venv\Scripts\python.exe -m pytest -q test_operator.py
..\..\..\.venv\Scripts\python.exe probe.py --device cpu --output-dir report-my-cpu-01
..\..\..\.venv\Scripts\python.exe probe.py --device cuda --output-dir report-my-cuda-01
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

build.py的--target选择cpu/cuda/all；build存本机生成exe/DLL。路径以脚本所在目录定位，编译工作目录也固定该目录。probe的报告相对路径以终端目录为准。缺工具先检查实际错误，再按工作区审批，不自行安装。

## 输入、输出与范围

公式y=x*scale+bias；只支持cpu/cuda、float32、连续Tensor，元素数≤2147483647，scale/bias有限且在float32范围内。Python检查设备与布局，Torch分配输出，原生函数只借用地址。C接口仍不能核验任意非零裸地址的真实长度，禁止直接传伪造地址。

两个参数是Python标量，只对输入Tensor登记梯度；没有AMP、vmap专门规则、多GPU或任意布局支持。本例是C接口DLL加torch.library注册，不是链接ATen C++ ABI的torch.utils.cpp_extension。opcheck检查不等于完整torch.compile生产执行已经验证。

GPU使用调用方当前流，启动返回错误码，实际异步执行在测试／probe同步处检查。不同流之间依赖和Tensor生命周期仍由使用方正确安排。

当前计时包含Python、注册、ctypes、分配与同步，不含编译和输入传输；结果不能泛化到纯核函数或端到端服务。作者结果见 [[90_参考与维护/单元验证/38 CPP算子与CUDA验证记录|验证记录]]，不代替学习者练习。
