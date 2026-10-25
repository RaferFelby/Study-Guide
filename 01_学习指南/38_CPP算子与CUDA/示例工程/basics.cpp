#include <iostream>
#include <stdexcept>
#include <vector>

template <typename Number>
Number sum_values(const std::vector<Number>& values) {
    Number total = 0;
    for (const Number value : values) {
        total += value;
    }
    return total;
}

void add_one(float& value) {
    value += 1.0f;
}

int main() {
    // vector 拥有元素内存；退出作用域时自动释放，不手动 delete。
    std::vector<float> values = {1.0f, 2.0f, 3.0f};
    add_one(values.at(0));
    const float* first = values.data();
    std::cout << "first=" << *first << " sum=" << sum_values(values) << '\n';
    try {
        std::cout << values.at(3) << '\n';
        return 1;
    } catch (const std::out_of_range&) {
        std::cout << "boundary=out_of_range\n";
    }
    return 0;
}
