"""公开政策只读任务；模拟角色先检查，资料不授予权限。"""

from uuid import uuid4

from adapter import SourceContractError, SourceUnavailable


class PolicyService:
    def __init__(self, source):
        self.source = source

    def answer(self, question, role):
        request_id = uuid4().hex
        result = {
            "request_id": request_id,
            "status": "invalid",
            "answer": "",
            "citations": [],
        }
        if not isinstance(question, str) or not question.strip() or len(question) > 500:
            result["answer"] = "请输入1～500字符的问题"
            return result
        if role != "reader":
            result.update(
                status="denied", answer="当前身份不能查询政策，请联系负责人员"
            )
            return result
        try:
            policies = self.source.fetch()
        except SourceUnavailable:
            result.update(
                status="unavailable", answer="政策服务暂不可用，请按人工流程核查"
            )
            return result
        except SourceContractError:
            result.update(
                status="unavailable", answer="政策资料格式异常，已停止自动答复"
            )
            return result
        # 两个显式规则只用于确定性教学，不是通用语义检索。
        topic = (
            "refund"
            if "退款期限" in question
            else "invoice"
            if "发票" in question
            else None
        )
        matches = [policy for policy in policies if policy["id"] == topic]
        if "VIP" in question or len(matches) != 1:
            result.update(status="refused", answer="现有资料不足以确认，请人工核实")
            return result
        policy = matches[0]
        result.update(
            status="answered",
            answer=policy["text"],
            citations=[
                {
                    "title": policy["title"],
                    "version": policy["version"],
                    "url": policy["url"],
                }
            ],
        )
        return result
