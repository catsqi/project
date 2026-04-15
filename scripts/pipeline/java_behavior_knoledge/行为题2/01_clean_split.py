import re
import json
import os


def parse_behavioral_v2(file_path):
    chunks = []
    source_ref = ""
    major_cat = ""
    sub_cat = ""

    # 使用 utf-8 编码读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 1. 提取全局来源链接 (#)
            if line.startswith('# '):
                source_ref = line.replace('# ', '').strip()

            # 2. 提取主分类 (###)
            elif line.startswith('### '):
                major_cat = line.replace('### ', '').strip()
                sub_cat = ""  # 切换主类时清空子类状态

            # 3. 提取子分类/公司名 (####)
            elif line.startswith('#### '):
                sub_cat = line.replace('#### ', '').strip()

            # 4. 提取题目 (匹配数字编号 1. 或 无序列表 -)
            elif re.match(r'^(\d+\.|-)\s+', line):
                # 去除行首的编号或符号
                content = re.sub(r'^(\d+\.|-)\s+', '', line).strip()

                # 组合最终分类名称
                full_category = f"{major_cat} -> {sub_cat}" if sub_cat else major_cat

                chunks.append({
                    "category": full_category,
                    "source_ref": source_ref,
                    "raw_content": content
                })
    return chunks


if __name__ == "__main__":
    # 定义绝对路径
    input_file = r"D:\大三作业\大三下作业\project\references\行为题\行为题2.md"
    output_dir = r"D:\大三作业\大三下作业\project\data\processed\行为题"
    output_file = os.path.join(output_dir, "行为题2.json")

    # 1. 确保目标目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 2. 执行解析
    if os.path.exists(input_file):
        processed_data = parse_behavioral_v2(input_file)

        # 3. 保存中间产物
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)

        print(f"解析完成！已成功从行为题2提取 {len(processed_data)} 道题目。")
        print(f"产物已保存至: {output_file}")
    else:
        print(f"错误：找不到文件 {input_file}")