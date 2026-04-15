import re
import json
import os
import uuid


def parse_behavioral_markdown(file_path):
    chunks = []
    source_link = ""
    current_category = ""
    current_question = ""

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line_stripped = line.rstrip()
        if not line_stripped:
            continue

        # 1. 提取全局来源链接 (##)
        if line_stripped.startswith('## '):
            source_link = line_stripped.replace('## ', '').strip()
            continue

        # 2. 提取能力维度考点 (####)
        if line_stripped.startswith('#### '):
            current_category = line_stripped.replace('#### ', '').strip()
            continue

        # 3. 提取主问题 (-)
        if line_stripped.startswith('- '):
            if current_question:
                # 保存上一题
                chunks.append({
                    "category": current_category,
                    "source_ref": source_link,
                    "raw_content": current_question.strip()
                })
            current_question = line_stripped.replace('- ', '').strip()
            continue

        # 4. 提取子问题/追问 (缩进的 -)
        if line.startswith('  - '):
            sub_q = line.strip().replace('- ', '')
            current_question += f"\n追问：{sub_q}"
            continue

    # 兜底保存最后一题
    if current_question:
        chunks.append({
            "category": current_category,
            "source_ref": source_link,
            "raw_content": current_question.strip()
        })

    return chunks


if __name__ == "__main__":
    # 1. 运行解析
    input_file = r"D:\大三作业\大三下作业\project\references\行为题\行为题1.md"
    raw_data = parse_behavioral_markdown(input_file)

    # 2. 定义目标输出目录和文件路径
    output_dir = r"D:\大三作业\大三下作业\project\data\processed\行为题"
    # 我们将中间文件保存为 json 格式，方便后续 Python 脚本读取并发送给大模型
    output_file = os.path.join(output_dir, "行为题.json")

    # 3. 确保目录存在 (exist_ok=True 表示如果目录已存在不会报错)
    os.makedirs(output_dir, exist_ok=True)

    # 4. 将中间物数据写入到指定目录
    with open(output_file, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 确保中文正常显示，indent=2 让生成的 JSON 文件有良好的可读性缩进
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    print(f"解析完成！共提取 {len(raw_data)} 道面试题。")
    print(f"中间数据已成功保存至: {output_file}")