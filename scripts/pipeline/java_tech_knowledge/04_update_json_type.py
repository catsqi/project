import json
import os


def rewrite_type_to_metadata(json_path, type_name="tech"):
    """
    读取指定的 JSON 文件，确保 type 字段只存在于 metadata 内部，并清理根路径的冗余字段
    """
    if not os.path.exists(json_path):
        print(f"找不到文件: {json_path}")
        return

    # 1. 读取原始数据
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("JSON 文件格式有误，读取失败")
            return

    if not isinstance(data, list):
        print("数据格式不是列表，请检查 JSON 结构")
        return

    # 2. 遍历处理
    count = 0
    for item in data:
        # A. 确保 metadata 字典存在
        if "metadata" not in item or not isinstance(item["metadata"], dict):
            item["metadata"] = {}

        # B. 在 metadata 内部设置 type
        item["metadata"]["type"] = type_name

        # C. 【关键】如果根路径存在 type，将其删除，保持数据纯净
        if "type" in item:
            del item["type"]

        count += 1

    # 3. 写回文件
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("-" * 50)
    print(f"处理完成：共处理 {count} 条记录")
    print(f"当前状态：type 字段已全部移至 metadata 内部")
    print(f"文件位置: {json_path}")


if __name__ == "__main__":
    # 请确保路径指向你的 Java技术知识.json
    target_file = r"/knowledge/Java后端知识库/Java技术知识.json"

    rewrite_type_to_metadata(target_file, "tech")