#include <cstdint>

// C ABI 避免跨编译器传递 C++ 对象；调用方仍须保证内存与长度真实有效。
extern "C" __declspec(dllexport) int affine_cpu(
    const float* input, float* output, std::int64_t count, float scale, float bias) {
    if (count < 0 || (count > 0 && (input == nullptr || output == nullptr))) {
        return -1;
    }
    for (std::int64_t index = 0; index < count; ++index) {
        output[index] = input[index] * scale + bias;
    }
    return 0;
}
