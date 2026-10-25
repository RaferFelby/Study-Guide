"""把已编译的 C ABI 函数注册成有明确输入契约的教学算子。"""

import ctypes
import math
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent
LIBRARIES = {}
MAX_FLOAT32 = torch.finfo(torch.float32).max


def check_input(value, scale, bias):
    if value.dtype != torch.float32:
        raise ValueError("本教学算子只支持 float32")
    if value.device.type not in ("cpu", "cuda"):
        raise ValueError("本教学算子只支持 cpu/cuda")
    if not value.is_contiguous():
        raise ValueError("输入必须连续；请明确调用 contiguous()")
    if value.is_neg():
        raise ValueError("输入不能带延迟负号视图；先 resolve_neg()")
    if value.numel() > 2147483647:
        raise ValueError("元素数超过教学上限")
    if not math.isfinite(scale) or not math.isfinite(bias):
        raise ValueError("scale 和 bias 必须有限")
    if abs(scale) > MAX_FLOAT32 or abs(bias) > MAX_FLOAT32:
        raise ValueError("scale 和 bias 超出 float32 有限范围")


def load_function(device):
    if device not in LIBRARIES:
        path = ROOT / "build" / f"affine_{device}.dll"
        if not path.is_file():
            raise RuntimeError(f"缺少 {path.name}；先运行 build.py --target {device}")
        library = ctypes.CDLL(str(path))
        function = getattr(library, f"affine_{device}")
        argument_types = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int64,
            ctypes.c_float,
            ctypes.c_float,
        ]
        if device == "cuda":
            argument_types.append(ctypes.c_void_p)
        function.argtypes = argument_types
        function.restype = ctypes.c_int
        LIBRARIES[device] = (library, function)
    return LIBRARIES[device][1]


@torch.library.custom_op("learning38::affine", mutates_args=())
def affine(value: torch.Tensor, scale: float, bias: float) -> torch.Tensor:
    check_input(value, scale, bias)
    output = torch.empty_like(value)
    function = load_function(value.device.type)
    arguments = [value.data_ptr(), output.data_ptr(), value.numel(), scale, bias]
    if value.device.type == "cuda":
        with torch.cuda.device(value.device):
            stream = torch.cuda.current_stream(value.device)
            status = function(*arguments, stream.cuda_stream)
    else:
        status = function(*arguments)
    if status != 0:
        raise RuntimeError(f"原生算子返回错误码 {status}")
    return output


@affine.register_fake
def affine_fake(value, scale, bias):
    check_input(value, scale, bias)
    return torch.empty_like(value)


def setup_context(ctx, inputs, output):
    ctx.scale = inputs[1]


def backward(context, gradient):
    return gradient * context.scale, None, None


affine.register_autograd(backward, setup_context=setup_context)
