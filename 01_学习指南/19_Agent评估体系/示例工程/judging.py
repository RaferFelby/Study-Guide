"""校准计算练习：示例标签不是人工盲测，也没有调用LLM。"""

from metrics import judge_agreement


def main():
    reference_fixture = [True, False, True, False, True, False, True, False]
    judge_fixture = [True, True, True, False, True, False, False, False]
    print("示例标签一致性", judge_agreement(reference_fixture, judge_fixture))
    # 故意只选左侧，交换候选次序后暴露位置依赖；不是质量评判。
    candidates = [("answer-a", "answer-b"), ("answer-b", "answer-a")]
    selected = [left for left, _ in candidates]
    print(
        "左侧偏好模拟", selected, "交换后是否仍选同一答案", selected[0] == selected[1]
    )


if __name__ == "__main__":
    main()
