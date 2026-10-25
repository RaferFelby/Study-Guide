"""使用已有编译器构建本目录示例，不下载、不在导入时编译。"""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_command(command):
    print(subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def build_cpu():
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("未找到 g++；先检查现有编译器，不自动安装")
    (ROOT / "build").mkdir(exist_ok=True)
    common = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror"]
    run_command(common + ["basics.cpp", "-o", "build/basics.exe"])
    run_command(common + ["-shared", "affine_cpu.cpp", "-o", "build/affine_cpu.dll"])
    run_command([str(ROOT / "build/basics.exe")])


def build_cuda():
    compiler = shutil.which("nvcc")
    if compiler is None:
        raise RuntimeError("未找到 nvcc；PyTorch 能用 CUDA 不代表装了 CUDA 编译器")
    installer_root = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
    vswhere = installer_root / "Microsoft Visual Studio/Installer/vswhere.exe"
    if not vswhere.is_file():
        raise RuntimeError("未找到 vswhere；需要获批安装 MSVC 与 Windows SDK")
    result = subprocess.run(
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    installation = result.stdout.strip()
    if not installation:
        raise RuntimeError("未检测到 MSVC C++ 工具链；请先阅读地图中的环境分支")
    vcvars = Path(installation) / "VC/Auxiliary/Build/vcvars64.bat"
    if not vcvars.is_file():
        raise RuntimeError("MSVC 安装不完整：缺少 vcvars64.bat")
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("未检测到可用 GPU，不能选择本机架构")
    major, minor = torch.cuda.get_device_capability()
    (ROOT / "build").mkdir(exist_ok=True)
    # 仅初始化这个编译子进程的环境，不改系统 PATH。
    batch = ROOT / "build/compile_cuda.cmd"
    batch.write_text(
        "@echo off\n"
        f'call "{vcvars}" > nul\n'
        "if errorlevel 1 exit /b %errorlevel%\n"
        f'"{compiler}" -std=c++17 -O2 --fmad=false -arch=sm_{major}{minor} '
        "--shared -Xcompiler /utf-8 affine_cuda.cu -o build/affine_cuda.dll\n"
        "exit /b %errorlevel%\n",
        encoding="utf-8",
    )
    run_command(["cmd.exe", "/d", "/c", str(batch)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["cpu", "cuda", "all"], default="cpu")
    options = parser.parse_args()
    if options.target in ("cpu", "all"):
        build_cpu()
    if options.target in ("cuda", "all"):
        build_cuda()


if __name__ == "__main__":
    main()
