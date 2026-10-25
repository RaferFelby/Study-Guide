"""编写最后一个规划单元；导入时不创建教材。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/38_CPP算子与CUDA"
MAP = "00 C++算子与CUDA学习地图"
LESSONS = [
    "01 编译第一个C++程序并读懂执行过程",
    "02 用引用指针与容器理解内存所有权",
    "03 检查Tensor布局并阅读原生算子路径",
    "04 连接C++函数并注册可求导算子",
    "05 编写CUDA核函数并检查线程边界",
    "06 校验算子并解释公平计时结果",
]


def write(name, body):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {path.stem}\ntags: [learning, cpp, cuda, beginner]\nupdated: 2026-10-14\n---\n\n# {path.stem}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../37_论文精读与技术趋势判断/00 论文精读与技术趋势判断学习地图|前一单元]]"
    )
    following = (
        f"[[{LESSONS[index + 1]}|下一讲]]"
        if index < 5
        else "[[../../../00_学习路线/总学习路线#七、推荐执行顺序与里程碑|进入项目与复习安排]]"
    )
    write(
        f"逐讲学习/{LESSONS[index]}.md",
        f"[[../{MAP}|单元地图]] · {previous} · {following}\n\n" + body,
    )


def main():
    write(
        f"{MAP}.md",
        r"""
## 现在学哪一讲

先打开 [[逐讲学习/01 编译第一个C++程序并读懂执行过程|第1讲]]，在 VS Code 的本单元示例工程终端编译 CPU 程序。第一步是运行编译器版本检查，不是安装新软件。看见 `first=2 sum=7` 和 `boundary=out_of_range`，并解释为什么和 Python 的直接运行不同，才算完成第一次跟做。

## 按顺序读六讲

1. [[逐讲学习/01 编译第一个C++程序并读懂执行过程|01 编译、类型、函数和入口]]
2. [[逐讲学习/02 用引用指针与容器理解内存所有权|02 引用、指针、RAII、模板与STL]]
3. [[逐讲学习/03 检查Tensor布局并阅读原生算子路径|03 shape、stride、连续内存与ATen阅读]]
4. [[逐讲学习/04 连接C++函数并注册可求导算子|04 原生CPU函数、C接口与PyTorch注册]]
5. [[逐讲学习/05 编写CUDA核函数并检查线程边界|05 实际CUDA核函数、网格、流和边界]]
6. [[逐讲学习/06 校验算子并解释公平计时结果|06 正确性、基准和项目迁移]]

六讲围绕同一公式 `output = input * scale + bias`，先让每个部分可理解，再连接起来。affine（仿射变换）在这里指“乘一个倍数，再加一个偏移”，不是完整神经网络。

## 前置知识与环境分支

需要函数、循环、异常、命令行与测试的基础，陌生时回到 [[../01_Python工程化/00 Python 工程化学习地图|单元01]]、[[../02_测试与实验复现/00 测试与实验复现学习地图|单元02]]。Tensor、自动微分与CPU/GPU先到 [[../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|单元06]]；流与同步不默认掌握，第5、6讲会补讲。

教材在 Obsidian 读，源码由 [[示例工程/README|代码导航]]进入，在 VS Code 阅读与运行。所有 Python 命令使用根 `.venv`；本单元没有新的 Python 包。

| 路径 | 所需资源 | 完成判断 |
| --- | --- | --- |
| 第1～4讲CPU | 已有GCC、共享PyTorch环境 | C++程序与CPU DLL可编译、算子结果和梯度正确 |
| 第5～6讲CUDA | NVIDIA GPU、nvcc、Windows MSVC和SDK | CUDA DLL真正编译并执行，边界与流测试通过 |
| 暂无GPU或编译工具 | 先做CPU、手算线程索引 | 明确记录未执行的GPU项目，不能写成实测 |

> [!info] 本机环境
> 作者检测到GCC15.2、CUDA Toolkit13.2；用户批准后安装VS2022 Build Tools的MSVC v143和Windows SDK。PyTorch仍为2.14.0+cu130，运行时13.0。安装记录和实际范围见 [[参考工程验证记录|作者验证]]。换机器先核对环境，缺依赖按工作区规则申请安装，不照抄系统安装命令。

## 必须掌握与稍后扩展

必须能说明编译与运行的区别、对象与地址的区别、连续内存为什么重要、指针和长度必须一致、线程怎么找到元素、如何验证与公平计时。必须亲自保留至少一次失败排查和一个对照结果。

模板元编程、完整C++类体系、复杂ATen宏、共享内存优化、Tensor Core、CUDA Graph、跨GPU通信与生产发布都是后续扩展。本单元的DLL是教学用C接口，由Python注册PyTorch算子；没有编译依赖ATen对象的C++扩展，也不宣称覆盖所有PyTorch子系统。

## 学完之后

这是规划中的第38个教材单元。进入 [[../../00_学习路线/总学习路线#七、推荐执行顺序与里程碑|项目执行顺序]]，按岗位选择主项目，把已学内容用于真实需求；从 [[../我的学习记录|学习记录]]找缺口复习。38个单元写完不等于你已经学完，也不等于所有进阶与生产环境都已验证。

[[../00 学习目录|学习目录]] · [[../37_论文精读与技术趋势判断/00 论文精读与技术趋势判断学习地图|前一单元]] · [[示例工程/README|源码]] · [[参考工程验证记录|作者验证]]
""",
    )
    lesson(
        0,
        r"""
## 本讲要解决什么问题

你以前把Python文件交给解释器运行。现在要把C++源码变成可执行文件，并能读懂最小程序；先不接PyTorch或GPU。前置是知道文件、终端、变量和函数，陌生时回到 [[../../01_Python工程化/00 Python 工程化学习地图|Python工程化地图]]。

阅读顺序：最小程序 → 编译运行 → 示例工程 → 排错 → 练习。

## 概念与直觉：源码先经过编译

C++源码是给人和编译器看的文字。编译器把它转换为机器能执行的代码；链接器把程序引用的库实现接好。编译和链接在本例由`g++`一次调用完成。`.exe`是Windows可执行文件，`.cpp`是源文件；改源码后必须重新编译，旧exe不会自动更新。

类型说明变量存什么。`int`在这里存整数，`float`存单精度小数，`void`表示函数不返回值。C++不会像Python那样让同一个普通变量任意换成另一种对象；先把数据类型写清楚，编译器才知道存储和运算方式。类型准确仍不代表算法一定正确。

## 完整最小示例

在VS Code打开工作区，进入`01_学习指南/38_CPP算子与CUDA/示例工程`，新建`lesson_01.cpp`，输入：

```cpp
#include <iostream>

int add_numbers(int left, int right) {
    return left + right;
}

int main() {
    int total = add_numbers(2, 3);
    std::cout << "total=" << total << '\n';
    return 0;
}
```

逐段读：`#include <iostream>`提供输出设施。`add_numbers`是函数名，两个`int`参数接收整数，`return`把和交给调用者。花括号界定一段函数体，每条普通语句用分号结束。

`main`是可执行程序的入口，运行时从它开始。先调用加法函数得到5，再赋给`total`。`std::cout`是标准输出对象；这里`<<`按顺序把文字、数字和换行写到终端，不是Python中的列表操作。`std::`表示名称属于标准库的命名空间，避免与自己定义的名字混淆。`'\n'`是一个换行字符；双引号包文字串，单引号包一个字符。

最后`return 0`表示程序正常结束。它不是给学习者显示“答案0”；输出答案来自前一行。

## 动手：在哪编译，在哪运行

VS Code菜单“终端→新建终端”，使用PowerShell。先切目录，再检查已有编译器；`--version`显示版本，不安装软件：

```powershell
Set-Location 'D:\AI-Agent算法学习\01_学习指南\38_CPP算子与CUDA\示例工程'
g++ --version
g++ -std=c++17 -O2 -Wall -Wextra -Werror lesson_01.cpp -o lesson_01.exe
.\lesson_01.exe
```

`-std=c++17`选择本例语言标准；`-O2`启用常用优化；`-Wall -Wextra`打开常见警告；`-Werror`把警告当作需要修复的问题；`-o`指定生成文件。它们是本工程选择，不是所有C++项目唯一允许的选项。预期最后输出`total=5`。先看编译命令是否成功，再运行exe；编译失败时旧exe还可能存在，不要误认作新版本运行成功。

接着编译正式示例。下面`build.py`调用已有编译器，`--target cpu`只构建CPU部分，完整源码在 [basics.cpp](../示例工程/basics.cpp) 和 [build.py](../示例工程/build.py)：

```powershell
..\..\..\.venv\Scripts\python.exe build.py --target cpu
```

预期包括`first=2 sum=7`、`boundary=out_of_range`。`build`目录放生成产物，不把二进制文件当教材源码提交。暂时知道这是三个数经过修改与求和的结果，第2讲解释内存细节。

也可以在同一目录新建`lesson_01.py`，用共享解释器运行以下完整代码，检查CPU构建文件已经出现：

```python
from pathlib import Path

program = Path("build/basics.exe")
print("CPU程序已生成:", program.is_file())
```

`Path`表示路径，当前相对路径以终端所在的示例工程为准。`is_file()`只确认文件存在，不能证明最新源码编译成功；真正运行仍看上面的构建命令与输出。预期为True。

## 常见错误：先定位阶段

- `g++`无法识别：检查`Get-Command g++`和已有安装位置；不要自行安装或改系统PATH。可以使用已有编译器的完整路径。若确实缺少，先准备安装方案获得批准。
- 缺分号、括号不配对：这是编译阶段错误，先看报错中的文件与行号，检查该行和前一行。
- 找不到源文件：终端不在示例工程，先`Get-Location`确认位置。
- 新输出没有变化：确认保存源码并成功重新编译，再运行正确exe。
- Python路径信息里出现`Failed to find real location...`：看退出码和后续结果。本机共享环境仍可执行；不要仅凭这一行认定依赖缺失。

## 练习、提示与完成标准

**跟做：** 编译并运行最小程序。标准：输出5，能指出入口、参数、返回值与终端所在目录。提示：不要把cpp交给Python解释器。

**独立：** 改为`add_numbers(7, -2)`，先预测，再重新编译。标准：输出5，并解释这是不同输入同一个和。

**迁移：** 写`multiply_numbers`函数并用3和4调用。标准：输出12，保留编译命令，能说明修改源码为什么需要重编译。

> [!example]- 参考答案与过程
> 跟做中`main→add_numbers→return 5→输出`；函数定义在前不代表它在入口前自行运行。独立题7+(-2)=5，必须保存并重新编译验证。迁移函数写成`int multiply_numbers(int left, int right) { return left * right; }`，入口的调用改为`multiply_numbers(3, 4)`。星号在此是乘法；下一讲会看到它在不同语法位置还可表示指针，不能只靠单个符号猜含义。

## 本讲完成判断

能独立创建、保存、编译、运行一个cpp，能区分编译错误和执行结果，并解释`main`与返回状态。下一讲再进入引用与内存。
""",
    )
    lesson(
        1,
        r"""
## 问题与前置

已经能编译程序，现在要解释“修改一个值为什么影响原容器”，以及“拿到地址之后谁负责释放内存”。前置是第1讲的类型、函数、花括号与入口。先读 [basics.cpp](../示例工程/basics.cpp)，不要先写`new/delete`或复杂类。

## 概念：值、引用、指针分开看

按值传参通常得到一个副本；改变参数不直接改变调用者那个值。引用是给已有对象的另一个访问名字。本例`float&`参数引用一个float，修改它会修改原元素。指针存对象地址；它可以为空，也可能指向已经不存在的内存，因此比“变量别名”多了有效性问题。

可以把引用想成同一抽屉的第二个标签，指针想成写着抽屉位置的纸。实际机制是对象存储和地址访问；标签类比不表达C++生命周期规则，更不能保证地址还有效。

## 从完整工程中找最小关键片段

```cpp
void add_one(float& value) {
    value += 1.0f;
}
```

`float& value`表示引用，不复制原数；`+=`把右边数加回左边。`1.0f`末尾f指明是float字面量；没有f的小数字面量通常是double。本例输入输出都按float保持一致。`void`表示不返回新数，因为目的就是修改传入对象。

工程入口先创建`std::vector<float> values = {1.0f, 2.0f, 3.0f};`。vector是标准库的动态数组，负责拥有和管理元素存储，`<float>`指定元素类型。`values.at(0)`取第0个元素并检查越界；`add_one(values.at(0))`之后三个数变为2、2、3。

下一行`const float* first = values.data();`取得第一个元素的地址。这里星号出现在声明中，表示指针；`*first`出现在表达式中，表示读取它指向的元素。`const float*`限制通过此指针修改元素，并不保证其他引用不能改原对象。空vector不允许解引用data返回的地址。

## RAII与STL：把生命周期交给拥有者

STL通常指C++标准模板库中的容器、算法等设施，本讲只用vector。RAII是“资源获取即初始化”的缩写：资源交给一个对象拥有，对象正常退出作用域或异常展开时，由析构过程释放资源。vector创建元素存储，离开main时自动释放；不要对`values.data()`手动delete，它不是交给你拥有的另一份内存。

这个机制适合内存、文件、锁等有明确生命周期的资源，但不保证程序绝不会泄漏，也不解决所有异步GPU生命周期问题。第5讲的GPU内存由PyTorch Tensor持有，不在核函数里随意释放。

**容易忽略的边界：** 保存`data()`指针后，如果vector扩容导致重新分配，旧指针可能失效。本工程取得指针之后不扩容；迁移时不能先记地址再任意`push_back`，也不能返回指向局部vector的地址。

## 模板：一个清晰的求和过程支持多种数值

读源码顶部`template <typename Number>`。Number是类型占位名，调用float容器时编译器生成相应实现；不是运行时随意更换变量类型。`const std::vector<Number>&`说明不复制整个容器，并限制函数通过此引用修改元素。

函数先设`Number total = 0`，再用`for (const Number value : values)`逐个读取元素，把值累加。这里冒号表示范围for循环，本次value按值取一个元素副本，修改它不改变容器。最后返回total。这个模板要求Number支持从0初始化和加法，并不是对所有类型都自动适用。

## 动手与预期结果

VS Code打开本工程`basics.cpp`，从main顺着执行，再用本工程终端：

```powershell
..\..\..\.venv\Scripts\python.exe build.py --target cpu
```

第一行结果`first=2 sum=7`，来自2+2+3；第二行`boundary=out_of_range`来自尝试`values.at(3)`，长度3的有效下标只有0、1、2。`try`内发生越界异常后进入`catch (const std::out_of_range&)`，输出已知错误。不是吞掉任意失败；若该访问没有抛异常，程序返回1使验证失败。

新建`lesson_02.py`，用以下完整Python例子对比“副本”与“修改容器”，只作直觉桥梁：

```python
values = [1.0, 2.0, 3.0]
copied_value = values[0]
copied_value += 1
print(values)
values[0] += 1
print(values, sum(values))
```

预期先`[1.0, 2.0, 3.0]`，再`[2.0, 2.0, 3.0] 7.0`。Python浮点对象和C++float存储模型不同；这个例子只帮助区分“改独立的数”与“改容器中的元素”，不能代替C++引用规则。

## 常见错误与修复

- 把`float&`改为`float`后first仍是1：函数只修改了副本，恢复引用并重编译。
- 用`values[3]`代替`at(3)`期待相同异常：普通下标访问不提供同样的越界检查；非法访问可能是未定义行为，不要靠崩溃学习。
- 手动delete容器地址：所有权错误；由vector释放自己的存储。
- 以为const让全局对象永不变：检查它修饰哪个访问路径，以及是否还有其他可修改引用。

## 练习与完成标准

**跟做：** 按顺序指出容器创建、引用修改、地址读取、模板求和、异常处理。标准：五步和输出均解释正确。

**独立：** 在自己复制的`lesson_02.cpp`里把`add_one`参数改成按值传递，再编译运行。提示：保留原工程不覆盖。标准：first1、sum6，说明副本退出函数后原元素未变。

**迁移：** 设计一个只读求和函数的接口，说明为什么传`const vector<float>&`，并写下空容器和指针失效规则。标准：不复制全容器、不修改输入、空容器不解引用、扩容后重新取得地址。

> [!example]- 参考答案与过程
> 引用版本修改values第0项为2，sum7；按值版本只把参数副本改成2，values仍1、2、3，所以sum6。只读接口可写`float sum_values(const std::vector<float>& values)`，实现沿用循环。空vector的sum是0；它不意味着data可以被解引用。容器负责释放，指针只是借用访问；借用不延长对象生命周期。

## 必须掌握与后续

必须分清对象、地址、借用和拥有者。智能指针、移动语义、模板推导细节可稍后学；当前不靠复杂封装掩盖内存规则。
""",
    )
    lesson(
        2,
        r"""
## 要解决的问题与前置

一个Tensor看起来是矩阵，底层却不是“每一行一个Python列表”。要把地址交给C++，先弄清元素存放顺序。前置是上一讲指针与所有权，以及 [[../../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|PyTorch基础]]中的Tensor与dtype。

本讲阅读顺序：shape与stride → 转置最小实验 → 为什么契约拒绝非连续输入 → 阅读ATen核心路径。

## 概念与直觉：shape不等于内存布局

shape（形状）是每个维度的长度；stride（步幅）是在某维下标加1，需要跨过多少个元素。二维索引(i,j)相对首元素的位置，在本例是`i * stride[0] + j * stride[1]`。步幅单位是元素，不是字节；float32的每个元素占4字节，算字节距离还要乘4。

连续Tensor按标准顺序紧密排列。转置可以只改变shape和stride，而共享原存储；看起来行列交换，不一定真的搬动数据。把它想成给同一排座位换一张编号表；实际Tensor还包含存储偏移、dtype和设备信息，这个类比不能表达全部视图机制。

## 完整最小实验与逐步解释

在本工程新建`lesson_03.py`，使用共享解释器运行：

```python
import torch

values = torch.arange(6, dtype=torch.float32).reshape(2, 3)
transposed = values.T
copied = transposed.contiguous()
print(values.tolist(), values.stride(), values.is_contiguous())
print(transposed.tolist(), transposed.stride(), transposed.is_contiguous())
print(copied.tolist(), copied.stride(), copied.is_contiguous())
print("转置共享地址:", values.data_ptr() == transposed.data_ptr())
print("连续化新地址:", copied.data_ptr() != transposed.data_ptr())
```

`arange(6)`生成0～5；`dtype=float32`让后续与C++的float约定一致。`reshape(2,3)`变成两行三列，`.T`是本例二维转置。`contiguous()`在必要时创建连续布局；已经连续时可能直接返回原Tensor，不保证每次都复制。`data_ptr()`给首元素地址，本例只比较，不自行读写任意地址。

预期三组列表分别为`[[0,1,2],[3,4,5]]`、`[[0,3],[1,4],[2,5]]`、与转置相同的列表；实际浮点打印带`.0`。步幅依次`(3,1)`、`(1,3)`、`(2,1)`；连续标志True、False、True；两个地址判断均True。地址的具体数值每次可不同，不作为验收常量。

现在手算：原values[1,2]的位置=1×3+2×1=5。transposed[2,1]的位置=2×1+1×3=5，也读到5。复制后的同一逻辑索引位置=2×2+1×1=5；此处数字恰相同不表示所有索引都同位置，transposed[1,0]的位置1，copied[1,0]的位置2。

## 为什么教学算子要拒绝非连续输入

本工程CPU/CUDA循环都按`input[index]`读一段连续float。它们没有收到shape、stride或广播规则，不能正确表达任意视图语义。Python边界明确检查float32和连续性；需要转置结果时由调用者写`.contiguous()`，让复制成本显式出现。

GPU地址也不能拿给CPU函数解引用。数值地址看起来都是整数，但属于不同设备的内存空间；必须根据`value.device.type`选择对应实现。误用不是一个可以安全catch的普通Python计算错误，可能损坏进程，因此边界校验必须在调用原生函数前完成。

## 读一个ATen核心路径：先看职责，再看宏

ATen是PyTorch中提供Tensor操作的C++核心部分。Dispatcher（分发器）根据算子注册、设备等信息选择实现；不要把所有工作都归给某一个核函数文件。

打开 [PyTorch官方threshold CUDA源码](https://github.com/pytorch/pytorch/blob/main/aten/src/ATen/native/cuda/ActivationThresholdKernel.cu)。这是2026-10-14阅读的main分支，不声称是本机wheel的精确源码；页面可变，做严格复现时应固定commit。这里读的是threshold路径，不能把它全部当成ReLU的唯一实现。

先在网页按Ctrl+F依次查`REGISTER_DISPATCH`、`threshold_kernel_cuda`、`AT_DISPATCH_ALL_TYPES_AND2`、`threshold_kernel_impl`、`gpu_kernel_with_scalars`。登记把stub接到设备实现；类型分支选择实际元素类型；模板得到对应类型实现；迭代设施按元素执行条件选择。真正的逐元素规则是“x不大于阈值时取替代值，否则取other”。当前只需解释这个核心路径，不展开每个宏。

TensorIterator是处理迭代布局等工作的原生设施，本工程简单指针循环没有复制它的全部能力。官方实现包含多种dtype与通用迭代支持；本例float32连续输入是教学限制，不是PyTorch算子普遍限制。到 [官方C++与CUDA算子教程](https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html) 可了解常见的`TORCH_LIBRARY`注册、ATen Tensor与编译扩展流程；本单元实际编译的是C接口DLL，下一讲会把两种边界说清楚。

## 动手与常见错误

先运行布局例子，再手写上面两个索引位置；打开本工程`operator_impl.py`的`check_input`，把三个限制和CPU循环对应起来。

- 误以为T总复制：用地址与stride一起验证，而不是仅看打印矩阵。
- 误以为连续化没有成本：复制也消耗时间与显存，在端到端评测里单独说明。
- 只看shape就给裸指针：补上dtype、device、contiguous和元素数检查。
- 网页文件或行号变了：记录访问日期与分支，按符号搜索；不要伪称已核对本机提交。

## 三层练习

**跟做：** 跑布局例子并解释三个stride。标准：能用元素位置公式解释转置共享存储。

**独立：** 算`values[1,0]`和`transposed[0,1]`的位置。提示：使用各自stride。标准：都得到位置3和元素3。

**迁移：** 为“接收转置矩阵的自定义函数”写两种方案，并列成本。标准：方案一先连续化并记录复制；方案二传shape/stride并实现正确索引，还需新边界测试，不只删掉检查。

> [!example]- 参考答案与过程
> 原矩阵(3,1)，第二行起点3；转置(1,3)，第二列起点3。连续副本(2,1)重排存储。独立题1×3+0=3，0×1+1×3=3。迁移若仍用本工程核函数，就只能选显式连续化；“支持任意stride”涉及索引计算和广播规则，属于新的实现工作。源码阅读卡可写：符号入口、类型选择、元素规则、布局设施、当前未展开的部分；不要写“已经懂全部ATen”。
""",
    )
    lesson(
        3,
        r"""
## 问题与前置

现在想让Python Tensor使用真正的C++循环，并且能反向传播。前置是连续float32内存、函数、引用与地址；本讲按“普通C++函数→C接口→ctypes→PyTorch注册→梯度”逐层增加概念。源码从 [affine_cpu.cpp](../示例工程/affine_cpu.cpp)、[operator_impl.py](../示例工程/operator_impl.py)进入。

## 第一层：谁分配，谁计算

Python先检查输入，再用`torch.empty_like(value)`分配新输出。C++只借用输入和输出地址，遍历count个元素，写`output[index] = input[index] * scale + bias`，不分配或释放Tensor内存。count是元素数，scale是乘数，bias是偏移。

`empty_like`的初值未定义；必须保证每个合法元素被写入。输入是const float指针，输出是可写float指针；两个指针只是访问路径，不变成新的内存拥有者。原生函数返回0代表正常，负数代表本例检测到的契约错误；Python检查状态并抛出有意义的异常。

## 第二层：C接口与动态库

DLL是Windows动态链接库，可由另一程序加载调用。ABI是编译后二进制接口约定，包括参数怎么传、符号如何命名。`extern "C"`让导出函数使用C链接约定，`__declspec(dllexport)`在Windows导出符号；它们不会把C++循环变成Python代码。

这里不跨接口传vector、异常或ATen Tensor对象，只传地址、64位元素数和float值。原因是GCC和MSVC的C++对象ABI不能随意混用；这个小C接口把边界压缩为明确的基础类型。本实现仍仅验证本机64位Windows，不能据此宣称所有平台或编译器组合都兼容。

原生函数能检查count负数和非空长度时的空指针，却不能从一个非零地址猜出内存实际大小。Python必须确保Tensor真实拥有至少count个元素且设备匹配。不要把随便造出的整数传给DLL，异常捕获无法保证进程安全。

## 第三层：ctypes声明必须先完整再调用

ctypes是Python标准库的外部函数调用工具。本工程`ctypes.CDLL`加载绝对定位到源码目录下build中的DLL，首次调用才加载；导入模块不会启动编译、训练或写结果。`argtypes`声明每个参数类型，`restype`声明返回类型。

对应关系是：地址→`c_void_p`，元素数→`c_int64`，两个标量→`c_float`，返回状态→`c_int`。CPU参数五个；GPU还会有第六个流地址。先构造完整`argument_types`列表，再一次赋给`function.argtypes`。不能赋值后再append期待内部调用配置自动更新；本次真实验证就发现这会把GPU第六参数按默认整数转换，导致大地址溢出。

源码里的LIBRARIES字典保存库与函数，避免重复加载，也明确保持动态库对象活着。它是本例的加载缓存，不保存输入Tensor或学习者状态。

## 第四层：注册算子与自动微分

算子是一个有名字和输入输出约定的计算操作。`@torch.library.custom_op("learning38::affine", mutates_args=())`的@叫装饰器，把下方函数接入PyTorch的注册机制；命名空间learning38避免和其他单元重名。空元组声明不修改输入，所以函数必须返回新的Tensor。它不自动把C++错误或梯度都修好。

fake实现只描述输出形状、dtype与设备，不读取真实地址或执行核函数，供相关框架检查使用。`register_fake`返回`empty_like(value)`并沿用契约检查。fake通过不等于真实核函数正确。

反向传播由`register_autograd`登记。对每个元素`y = x * scale + bias`，dy/dx=scale，上游梯度g传回`g * scale`。setup_context把scale放入ctx（本次求导调用的上下文），backward返回三个位置对应的梯度：Tensor输入的梯度，两个Python浮点标量返回None。这里不能学习scale/bias；若要训练它们，必须改为Tensor参数并设计对应梯度，不能只把None改成一个数。

本工程按 [PyTorch官方注册接口](https://docs.pytorch.org/docs/2.14/library.html) 使用custom_op、fake与autograd；`opcheck`检查注册契约，数学正确性另用对照。生产中纯PyTorch表达式通常直接写`value * scale + bias`即可，本例为学习外部原生实现的连接机制。

## 完整调用示例、操作与结果

先在本工程终端执行`..\..\..\.venv\Scripts\python.exe build.py --target cpu`，然后新建`lesson_04.py`运行：

```python
import torch
from operator_impl import affine

value = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
result = affine(value, 2.0, 1.0)
print(result.detach().tolist())
result.sum().backward()
print(value.grad.tolist())
print("输入没有被改:", value.detach().tolist())
```

预期结果`[3.0,5.0,7.0]`，梯度`[2.0,2.0,2.0]`，输入仍`[1.0,2.0,3.0]`。detach得到不参与求导记录的视图，方便显示；sum把结果变成一个标量损失，backward计算输入梯度。这里没有优化器或训练轮次，因为本讲只验证一个局部算子。

## 报错排查与范围

- 缺`affine_cpu.dll`：先构建CPU，确认编译成功，不手动复制来历不明的DLL。
- dtype错误：本例只支持float32，明确转换后再调用，同时理解精度变化。
- 非连续输入：检查stride和is_contiguous，显式调用contiguous并记录复制成本。
- 标量超出float32范围：即使Python浮点数有限，转换为C float也可能溢出；缩小参数或另行实现更高精度接口。
- DLL加载失败：确认64位Python/编译目标一致，查看依赖和实际错误；不要盲目改系统路径。
- 梯度缺失：核对requires_grad、sum与注册；本例不会学习两个Python标量。
- 文档里看到`TORCH_LIBRARY`：那是常见C++注册扩展路线，涉及ATen头文件、链接和工具链兼容。本例没有编译这种扩展；不能把“C接口注册成功”写成“所有ATen扩展都验证了”。

## 练习与答案

**跟做：** 跑完整调用，记录值、梯度和未修改输入。标准：三者全部正确。

**独立：** scale=-2、bias=4，输入仍1、2、3。提示：先手算再运行。标准：结果2、0、-2；梯度全部-2。

**迁移：** 说明如何支持float64或可训练scale。标准：同时提到原生数据类型、边界、注册与数学验证，不能只删除dtype检查。

> [!example]- 参考答案与过程
> 跟做计算1×2+1=3等，sum对每个y的上游梯度是1，故x梯度2。独立题三项分别2、0、-2，bias不影响dy/dx。float64需要C++double指针和匹配接口、输出dtype、CPU/CUDA实现与测试；可训练scale需要Tensor输入，dL/dscale是各元素g×x之和，并保存必要状态。本例没有实现这些扩展。
""",
    )
    lesson(
        4,
        r"""
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
""",
    )
    lesson(
        5,
        r"""
## 问题与前置

自定义CUDA真的跑起来了，但它是不是正确、是不是更快？前置是前五讲的公式、契约与异步。阅读顺序：正确性清单 → 实际测试 → 计时口径 → 对照报告 → 独立解释与项目迁移。

## 先证明检查了什么

数值对照使用同一输入、dtype、scale与bias，比`affine(value,2,1)`和`value*2+1`；浮点通常用容差而不是要求位级相同。本工程`assert_close`采用明确容差；当前报告误差0只是这组有限输入的结果，不证明所有输入位级相等。

边界至少包括空Tensor、标量、一元素、257非整块、多维连续输入；拒绝非连续与错误dtype；scale/bias非有限或超float32范围时报错。反向检查sum的输入梯度=scale；`opcheck`另查PyTorch注册契约，它不代替数学对照。非默认CUDA流检查输入、核函数和后续运算在所选流的次序。

裸指针API不能验证任意地址是否真的有效，因此失败测试只用可安全检测的空指针与负数，不故意访问随机地址制造进程崩溃。输入含NaN/Inf时传播行为还需独立设计检查；本次没有把“有限参数”误写成“保证输出永远有限”，很大输入乘法也可能溢出。

## 动手：运行测试和保存报告

在本工程VS Code PowerShell，先确保CPU/CUDA都已成功构建，再运行：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest -q test_operator.py
..\..\..\.venv\Scripts\python.exe probe.py --device cpu --output-dir report-my-cpu-01
..\..\..\.venv\Scripts\python.exe probe.py --device cuda --output-dir report-my-cuda-01
```

pytest运行具体本单元测试文件，避免其他单元包重名。作者的CPU/GPU测试全通过才进入报告；没有GPU时应明确记录对应项目未运行，不修改设备参数来冒充GPU。`--output-dir`指定JSON输出目录，用自己新的目录名保留结果；不要覆盖作者目录来伪造亲自完成。

probe先验证再计时，验证失败会停止。每种实现预热5次，让首次加载与启动不主导；测15次取中位数，减少单次波动影响。CPU单次用perf_counter墙钟；CUDA计时前后同步，避免只测任务提交。每次还包括输出分配、Python调用、注册分发和ctypes，**不是纯核函数时延**。

编译不在计时范围，输入已在目标设备，不计CPU→GPU传输或contiguous复制；真实应用如果包含这些步骤，需另测端到端。同步整个设备可能受其他GPU任务干扰，先关闭自己可控的计算负载并记录状态，不擅自中断别人的程序。此计时不是专业微基准的全部要求。

## 完整读取报告示例

先运行自己的CPU报告，再创建`lesson_06.py`：

```python
import json
from pathlib import Path

report = json.loads(Path("report-my-cpu-01/report.json").read_text(encoding="utf-8"))
for row in report["rows"]:
    ratio = row["native_over_custom"]
    print(row["count"], row["max_error"], round(ratio, 3))
```

read_text读文件，json.loads还原字典；rows每项是同一规模的对照。比例`native_ms/custom_ms`大于1才表示当前自定义调用较快，小于1表示较慢，等于1约相同。预期元素数0、1、257、1048576依次出现；误差本机当前为0，比例随负载变化，不要求你的数字与作者相同。

## 作者实际结果该如何解释

详细数值见 [[../参考工程验证记录|作者记录]]。本机初次CPU百万元素自定义约0.855ms、原生0.710ms；CUDA自定义约0.147ms、原生0.103ms，初次两设备自定义都慢。交付复跑CPU约0.823ms对0.930ms，CPU比例变为约1.13；GPU仍约0.158ms对0.107ms较慢。小输入两次都没有优势；大输入CPU快慢变化提示重复测量与系统状态的重要性，不能只挑有利的一次宣称稳定收益。

单个核函数理论上可减少中间结果的读写；本例每元素读4字节写4字节，理想数据流量8N字节，原生两步表达式理论上还写读中间数组。但缓存、调度、输出分配、Python注册和C接口开销会影响最终时间，所以不能把理论字节数直接当实测带宽。当前比较也没有包含torch.compile可能的融合，不对最优原生实现下结论。

CPU原生可能采用多线程或向量化，自己的简单循环不自动等于优化库；报告记录本机PyTorch CPU线程数24。CPU结果有波动，GPU单核省下的工作在本输入与接口开销下未形成收益。要研究下一步，分别改变规模、块大小、融合选项、计时口径或接口，并一次只改变一个条件；先正确再比较。没有稳定收益证据时可以保留原生表达式。

## 常见错误

- 用一次测量得出百分比提升：增加重复、预热，保存完整条件和对照，不隐藏慢的结果。
- 只CUDA启动不等待：测到提交时间，补同步或明确使用正确的GPU事件口径。
- 自定义计入复制、原生不计：统一范围；端到端与设备驻留结果分开列。
- 只输出正确就说支持训练：检查梯度、注册、布局和错误路径；本例只支持输入Tensor求导。
- 报告中编译时间“忽略”：设备驻留调用不包含它；部署启动时间另记，不能删掉真实用户等待成本。

## 练习、答案与完成标准

**跟做：** 跑测试与两设备报告，写一段含公式、输入规模、误差、时间口径和结果的结论。标准：清楚区分核函数与整个算子调用，不把慢写成快。

**独立：** 若原生0.12ms、自定义0.20ms，算比例并解释。提示：先标清分子分母。标准：0.6，自定义更慢；自定义用时是原生约1.67倍。

**迁移：** 把同一公式放到自己的项目中，决定用原生还是自定义。标准：先有真实调用频率、dtype/布局、正确性和端到端对照；没有收益就不额外维护原生工具链。

> [!example]- 参考答案与过程
> 结论示例：在本机float32连续设备驻留输入下，自定义C++/CUDA实现与原生公式在已测规模内通过对照；同步墙钟包含分配与接口开销，GPU当前较慢，CPU百万元素两次快慢关系变化，不足以支持稳定优化收益。0.12/0.20=0.6，0.20/0.12≈1.67。迁移报告需写未测范围，如混合精度、任意stride、多GPU、生产并发与完整编译图执行，不能把本机机制实验扩大成普遍结论。

## 38个单元之后从哪里继续

现在完成的是教材主线编写末端，你的实际进度仍以 [[../../我的学习记录|学习记录]]为准。先补没有亲自完成的基础，再到 [[../../../00_学习路线/总学习路线#七、推荐执行顺序与里程碑|项目与里程碑]]按岗位选项目；对照 [[../../../00_学习路线/总学习路线#八、分岗位求职验收|岗位验收]]准备可运行成果与失败分析。无需为编号写完而假定掌握全部内容。
""",
    )
    write(
        "示例工程/README.md",
        r"""
## 从哪里开始

Obsidian读 [[../00 C++算子与CUDA学习地图|学习地图]]。VS Code在本目录阅读、编译和运行，Python统一根共享环境。

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

当前计时包含Python、注册、ctypes、分配与同步，不含编译和输入传输；结果不能泛化到纯核函数或端到端服务。作者结果见 [[../参考工程验证记录|验证记录]]，不代替学习者练习。
""",
    )


if __name__ == "__main__":
    main()
