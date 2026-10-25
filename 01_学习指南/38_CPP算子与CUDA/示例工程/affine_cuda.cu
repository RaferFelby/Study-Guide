#include <cuda_runtime.h>
#include <cstdint>

__global__ void affine_kernel(
    const float* input, float* output, std::int64_t count, float scale, float bias) {
    const std::int64_t index =
        static_cast<std::int64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (index < count) {
        output[index] = input[index] * scale + bias;
    }
}

extern "C" __declspec(dllexport) int affine_cuda(
    const float* input, float* output, std::int64_t count,
    float scale, float bias, void* stream_pointer) {
    if (count < 0 || (count > 0 && (input == nullptr || output == nullptr))) {
        return -1;
    }
    if (count == 0) {
        return 0;
    }
    // 教学上限保证一维网格和后面的整数转换安全。
    if (count > 2147483647LL) {
        return -2;
    }
    const int threads = 256;
    const int blocks = static_cast<int>((count + threads - 1) / threads);
    auto stream = static_cast<cudaStream_t>(stream_pointer);
    affine_kernel<<<blocks, threads, 0, stream>>>(input, output, count, scale, bias);
    // 这里只检查提交错误；异步执行错误由 Python 的同步检查暴露。
    return static_cast<int>(cudaGetLastError());
}
