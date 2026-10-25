"""作者整理的阅读卡；来源事实与本地实验分开，不复制论文全文。"""

import copy

PAPERS = [
    {
        "id": "transformer",
        "title": "Attention Is All You Need",
        "source": "https://arxiv.org/abs/1706.03762v7",
        "locator": "Abstract; Section 3; translation experiments",
        "reading_depth": "overview_with_prior_unit_08",
        "problem": "怎样在序列任务中并行处理位置间关系。",
        "method": "用注意力与前馈组成模型，并提供位置表示。",
        "evidence": "原文在机器翻译等任务报告结果；本卡没有重新训练原模型。",
        "limitations": "原任务和资源条件限定证据范围，不能直接证明所有业务可用。",
    },
    {
        "id": "lora",
        "title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "source": "https://arxiv.org/abs/2106.09685v2",
        "locator": "Section 4.1; Section 4.2; Section 7.1/Table 5",
        "reading_depth": "selected_method_and_experiment_sections",
        "problem": "减少任务适配时可训练参数与维护多份模型的负担。",
        "method": "冻结基础权重，训练低秩矩阵，并在条件满足时合并线性更新。",
        "evidence": "方法公式支持合并；原实验对比任务分数和适配预算。本地另检查小矩阵等价性。",
        "limitations": "低秩效果依赖任务、目标层与rank；机制验证不是全量模型质量复现。",
    },
    {
        "id": "cot",
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "source": "https://arxiv.org/abs/2201.11903v6",
        "locator": "Abstract; method and task experiments to read next",
        "reading_depth": "abstract_overview_with_prior_unit_32",
        "problem": "怎样在提示中组织多步任务示范。",
        "method": "示范包含中间推导，再生成回答。",
        "evidence": "摘要报告多类推理任务实验；本卡未独立重跑。",
        "limitations": "生成的解释可能出错，不能把文字过程当真实性或正确性保证。",
    },
    {
        "id": "react",
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "source": "https://arxiv.org/abs/2210.03629v3",
        "locator": "Abstract; task trajectories to read next",
        "reading_depth": "abstract_overview_with_prior_unit_34",
        "problem": "怎样让计划与环境反馈相互更新。",
        "method": "交替组织推理记录、动作和环境观察。",
        "evidence": "原文报告问答及交互任务；本卡没有复现其完整环境。",
        "limitations": "动作执行和结果可信度仍需检查，不能从轨迹形式推出安全可靠。",
    },
    {
        "id": "dpo",
        "title": "Direct Preference Optimization: Your Language Model is Secretly a Reward Model",
        "source": "https://arxiv.org/abs/2305.18290v3",
        "locator": "Abstract; objective derivation to read next",
        "reading_depth": "abstract_overview_with_prior_unit_33",
        "problem": "怎样用回答偏好对调整模型。",
        "method": "将偏好优化写为相对参考模型的训练目标。",
        "evidence": "原文报告偏好相关任务；本地先前单元有微型诊断，不是论文全实验。",
        "limitations": "偏好标签和更新强度影响质量，偏好胜出不等于事实正确。",
    },
    {
        "id": "agent_survey",
        "title": "A Survey on Large Language Model based Autonomous Agents",
        "source": "https://arxiv.org/abs/2308.11432v7",
        "locator": "Abstract; architecture and evaluation taxonomy to read next",
        "reading_depth": "abstract_overview_with_prior_agent_units",
        "problem": "怎样整理Agent架构、应用与评估研究。",
        "method": "按系统要素和研究主题梳理相关工作。",
        "evidence": "综述提供分类和文献入口，不能当某个系统的对照实验。",
        "limitations": "覆盖受检索时间与范围限制，当前工程适配必须另行核查。",
    },
]


def reading_cards():
    return copy.deepcopy(PAPERS)
