"""用工单列表观察赋值、浅复制、深复制与快照。"""

from copy import deepcopy


def add_tag_to_copy(ticket: dict, tag: str) -> dict:
    """复制一条含 tags 列表的工单，再修改副本；原工单保持不变。"""
    if not isinstance(ticket, dict):
        raise TypeError("工单必须是字典")
    if not isinstance(ticket.get("tags"), list):
        raise TypeError("工单的 tags 必须是列表")
    if not isinstance(tag, str):
        raise TypeError("标签必须是文字")
    if not tag.strip():
        raise ValueError("标签必须是非空文字")
    result = deepcopy(ticket)
    result["tags"].append(tag)
    return result


def main() -> None:
    original = [{"id": "T001", "tags": ["new"]}]
    alias = original
    shallow = original.copy()
    deep = deepcopy(original)
    print("外层同一对象", alias is original, shallow is original, deep is original)
    print("内层同一对象", shallow[0] is original[0], deep[0] is original[0])

    shallow[0]["tags"].append("urgent")
    print("原始标签", original[0]["tags"])
    print("深复制标签", deep[0]["tags"])
    shallow.append({"id": "T002", "tags": []})
    print("外层长度", len(original), len(shallow))

    changed = add_tag_to_copy(original[0], "checked")
    print("修改副本", changed["tags"])
    print("保留原始", original[0]["tags"])


if __name__ == "__main__":
    main()
