---
title: 第 5 讲：编写CUDA核函数并检查线程边界
tags: [learning, cpp, cuda, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 5 讲：编写CUDA核函数并检查线程边界

> [!nav] 页面导航
> [[01_学习指南/38_CPP算子与CUDA/00 C++算子与CUDA学习地图#学习顺序|单元 38：C++算子与CUDA]] · [[01_学习指南/38_CPP算子与CUDA/逐讲学习/04 连接C++函数并注册可求导算子|上一讲]] · [[01_学习指南/38_CPP算子与CUDA/逐讲学习/06 校验算子并解释公平计时结果|下一讲]]

## 问题、前置与阅读顺序

CPU循环一个元素一个元素计算，现在让GPU的多个线程共同处理。前置是第4讲地址、元素数、算子契约和输出分配。阅读顺序：环境检查 → 手算线程位置 → 核函数 → 流与错误 → 实际构建运行。

CUDA是NVIDIA的GPU计算平台；kernel（核函数）是由GPU线程执行的函数。PyTorch能使用CUDA运行时，不代表机器有nvcc编译器；nvcc还需要受支持的宿主C++工具链。本机Toolkit13.2与torch运行时13.0是不同组件，不因版本字符串不同就自行升级。

## 环境检查：先看实际工具

VS Code本工程终端运行：

```powershell
Get-Command nvcc -ErrorAction SilentlyContinue
nvcc --version
..\..\..\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"
```

第一条只查已有命令；第二条查编译器版本；第三条查共享PyTorch运行环境。Windows的nvcc宿主工具支持范围看 [NVIDIA CUDA13.2官方安装指南](https://docs.nvidia.com/cuda/archive/13.2.0/cuda-installation-guide-microsoft-windows/index.html)。本机用户批准安装MSVC与SDK后已实际编译；换机器时缺工具先申请方案，不把GCC能编译CPU等同于nvcc宿主一定兼容。

## 线程、块、网格：从257个元素开始

thread是一次核函数的执行实例；block是组织一组线程的块；grid是本次启动的全部块。本例一维，每块256线程。`threadIdx.x`是块内编号0～255，`blockIdx.x`是块编号，`blockDim.x`是每块线程数。

线程处理的位置：`index = blockIdx.x * blockDim.x + threadIdx.x`。count257需2块，共512个线程编号，但只有0～256合法。`if (index < count)`确保多出来的线程不读写数组。它不是性能装饰，而是内存安全和完整输出的必要条件。

向上取整块数用整数公式`(count + threads - 1) / threads`，C++整数除法舍弃小数。257+255=512，512/256=2；256+255=511，511/256=1。count0不启动，避免0块的非法配置。调用还限制count≤2147483647，使块数转换在本例边界内。

## 最小关键核函数与逐步解释

完整文件在 [affine_cuda.cu](../示例工程/affine_cuda.cu)，不要把片段当成可独立执行脚本：

```cpp
__global__ void affine_kernel(
    const float* input, float* output, std::int64_t count, float scale, float bias) {
    const std::int64_t index =
        static_cast<std::int64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (index < count) {
        output[index] = input[index] * scale + bias;
    }
}
```

`__global__`是CUDA扩展，标记CPU可启动的GPU核函数。`static_cast<std::int64_t>`先把块编号转64位再乘，避免索引中间计算按较小整数类型溢出。每个合法线程读一个float、写一个float；没有线程写别人的位置，所以此公式不需要线程间同步。

相邻线程访问相邻元素，有利于合并内存访问：硬件可把邻近请求组织成较少的内存事务。不是所有相邻代码访问都保证同样收益，实际还受对齐、缓存和硬件影响。这里只用全局内存和简单逐元素公式，不引入共享内存、warp同步或矩阵专用硬件。

## 启动、流与异步错误

启动语法`affine_kernel<<<blocks, threads, 0, stream>>>(...)`提供块数、每块线程数、额外共享内存字节0和stream。流是GPU任务的有序提交队列；同一流先后的输入生成、核函数和后续运算按该流次序安排，不同流的依赖要明确建立。

Python取得`torch.cuda.current_stream(value.device).cuda_stream`传给C接口，而不是在原生函数里擅自使用默认流。默认流小例子可能碰巧工作，非默认流测试才会暴露接口是否尊重调用方的顺序。本例的Torch Tensor拥有内存，核函数借用地址；跨流使用时还需处理等待与生命周期，不是只传一个地址就完成所有并发管理。

GPU启动通常异步返回；`cudaGetLastError`检查启动阶段的错误，异步执行错误要在同步点暴露。本工程不在每次算子里强制同步，以保留正常排队能力；验证和计时脚本在明确边界调用`torch.cuda.synchronize()`。它等待设备任务完成，也可能等待同GPU其他工作，下一讲解释计时口径。

## 构建、完整调用与预期

在本工程终端：

```powershell
..\..\..\.venv\Scripts\python.exe build.py --target cuda
```

build.py使用vswhere查MSVC安装，调用vcvars64初始化**编译子进程**环境，不永久修改系统PATH；根据当前GPU能力选择sm架构。`--shared`生成DLL，`--fmad=false`关闭乘加融合方便本例与两步表达式对照，`-Xcompiler /utf-8`让宿主编译器正确读中文注释。这个选项是实际修复编码失败，不修改系统代码页；性能探索时改变融合设置也应重做数值和基准验证。

构建成功出现`build/affine_cuda.dll`且命令退出0。新建`lesson_05.py`运行：

```python
import torch
from operator_impl import affine

value = torch.arange(257, device="cuda", dtype=torch.float32)
result = affine(value, 2.0, 1.0)
torch.cuda.synchronize()
torch.testing.assert_close(result, value * 2 + 1)
print(result[:3].tolist(), result[-1].item(), result.numel())
```

预期`[1.0,3.0,5.0] 513.0 257`。`.item()`把一个元素读成Python数，可能涉及等待；不把这样的显示放进单纯核函数计时。这里assert_close失败会抛异常，输出不是唯一成功依据。

## 常见错误与修复

- 缺MSVC：先检查vswhere，按批准的工具链方案处理；已有CUDA运行环境不等于可编译。
- 源码中count突然“未定义”并伴C4819：检查中文注释的编码与宿主`/utf-8`，不要为了消警告删除关键逻辑。
- 非默认流地址报`int too long to convert`：核对第六个ctypes参数完整声明为c_void_p，并在列表构造完成后一次赋值。
- 结果尾部错误：检查257的块数和index<count，不能仅用256整倍数输入验证。
- 不支持的GPU架构或驱动错误：记录GPU、nvcc、torch运行时及原始错误，先确认兼容方案，不能静默改用CPU冒充GPU成功。

## 三层练习与参考答案

**跟做：** 构建并跑257元素验证。标准：正确值、元素数和对照通过，记录环境。

**独立：** 手算count255、256、257、0的块数与无效线程数。提示：0专门不启动。标准：结果分别(1,1)、(1,0)、(2,255)、(0,0)。

**迁移：** 保留原源码，把副本每块线程改为128，预测257的网格并重做值检查。标准：3块、384线程、127无效线程，不能直接宣称128更快。

> [!example]- 参考答案与过程
> count255只需1块，编号255无效；256全部合法；257有两块，后一块只有threadIdx0合法。0返回成功而不启动。128线程时ceil(257/128)=3，384-257=127。改变块大小属于配置实验，要先重编译再验证，也不能假设不同硬件、不同规模的最佳值一样。

## 继续学习

> [!next] 下一步
> [[01_学习指南/38_CPP算子与CUDA/逐讲学习/06 校验算子并解释公平计时结果|下一讲：校验算子并解释公平计时结果]]

> [!info]- 练习与记录
> [[01_学习指南/38_CPP算子与CUDA/示例工程/README#代码导航|查看源码]] · [[01_学习指南/38_CPP算子与CUDA/示例工程/README#环境与运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 38：C++、算子与CUDA|本单元完成清单]]
