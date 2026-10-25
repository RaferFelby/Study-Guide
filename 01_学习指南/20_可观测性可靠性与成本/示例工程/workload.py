from copy import deepcopy


def make_workload():
    tasks = []
    for index in range(12):
        scenario = (
            "lookup"
            if index < 6
            else ("vip" if index < 8 else ("conflict" if index < 10 else "timeout"))
        )
        question = "refund VIP" if scenario == "vip" else "refund"
        documents = [{"id": f"policy-{index}", "days": 10 + index}]
        if scenario == "conflict":
            documents.append({"id": f"legacy-{index}", "days": 30 + index})
        expected_status = {
            "lookup": "answered",
            "vip": "refused",
            "conflict": "needs_review",
            "timeout": "failed",
        }[scenario]
        tasks.append(
            {
                "task_id": f"task-{index}-first",
                "input": {
                    "owner": "alice" if index % 2 == 0 else "bob",
                    "question": question,
                    "knowledge_version": f"v1-service-{index}",
                    "documents": documents,
                    "timeout": scenario == "timeout",
                },
                "gold": {
                    "status": expected_status,
                    "days": 10 + index if scenario == "lookup" else None,
                },
            }
        )
    repeated = deepcopy(tasks)
    for task in repeated:
        task["task_id"] = task["task_id"].replace("first", "repeat")
    return tasks + repeated
