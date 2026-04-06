import os
import json


def merge_json_files(input_dir, output_filepath):
    """
    读取指定目录下的所有 JSON 文件，将它们合并成一个列表，并保存到目标路径。
    """
    if not os.path.exists(input_dir):
        print(f"找不到输入文件夹: '{input_dir}'")
        return

    master_knowledge_base = []
    file_count = 0

    print(f"开始合并，正在扫描输入目录...\n" + "=" * 60)

    # 1. 遍历所有的 json 文件
    for filename in os.listdir(input_dir):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(input_dir, filename)

        # 2. 读取单个文件并拼接
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # 确保读取到的是列表形式的数据
                if isinstance(data, list):
                    master_knowledge_base.extend(data)
                    file_count += 1
                    print(f"  成功合并: {filename} (含 {len(data)} 条数据)")
                else:
                    print(f"格式不是列表，跳过: {filename}")
            except json.JSONDecodeError:
                print(f"文件 {filename} 解析失败，可能是格式有误，已跳过。")

    # 3. 确保输出文件所在的目录存在
    output_dir = os.path.dirname(output_filepath)
    os.makedirs(output_dir, exist_ok=True)

    # 4. 将总数据写入最终的 JSON 文件
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(master_knowledge_base, f, ensure_ascii=False, indent=2)

    # 5. 打印合并结果报告
    print("=" * 60)
    print(f"知识库合并彻底完成！")
    print(f"统计结果: 成功读取了 {file_count} 个文件，总计合并了 {len(master_knowledge_base)} 条面试题数据。")
    print(f"最终题库已安全存放在: \n   -> {output_filepath}")


if __name__ == "__main__":
    # 使用 r"" 原始字符串，防止 Windows 路径中的反斜杠 \ 被转义
    INPUT_DIR = r"D:\大三作业\大三下作业\project\data\output"
    OUTPUT_FILE = r"D:\大三作业\大三下作业\project\knowledge\Java后端知识库\Java技术知识.json"

    merge_json_files(INPUT_DIR, OUTPUT_FILE)