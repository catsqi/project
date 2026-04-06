import os
import re
import json


def process_and_split(input_filepath, output_filepath):
    """
    读取原始 Markdown，进行预处理清洗，按标题切分，并保存为 JSON 中间物
    """
    # ================= 1. 加载原始文件 =================
    if not os.path.exists(input_filepath):
        print(f"❌ 找不到输入文件: {input_filepath}")
        return

    with open(input_filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # ================= 2. 预处理清洗 (Cleaning) =================
    # 剔除开头由 --- 包裹的 YAML 元数据
    text = re.sub(r'^---[\s\S]*?---\n', '', text)

    # 剔除 HTML 注释 (已修复)
    text = re.sub(r'', '', text)

    # 剔除标题中干扰提问语气的特殊符号 ⭐️
    text = text.replace('⭐️', '')

    # ================= 3. 结构化切割 (Splitting) =================
    processed_chunks = []

    # 第一层切割：按二级标题 (##) 切分大类
    h2_blocks = re.split(r'\n##\s+', text)

    for h2_block in h2_blocks:
        if not h2_block.strip():
            continue

        # 提取当前大类的标题和剩余内容
        lines = h2_block.split('\n', 1)
        category_title = lines[0].strip()
        h2_body = lines[1] if len(lines) > 1 else ""

        # 过滤掉文档末尾的“参考”等非面试题模块
        if category_title == "参考" or category_title == "总结":
            continue

        # 第二层切割：按三级标题 (###) 切分具体的面试题
        h3_blocks = re.split(r'\n###\s+', h2_body)

        for h3_block in h3_blocks:
            if not h3_block.strip():
                continue

            # 提取面试题标题和解答正文
            h3_lines = h3_block.split('\n', 1)
            question_title = h3_lines[0].strip()
            question_body = h3_lines[1].strip() if len(h3_lines) > 1 else ""

            # 将干净的数据组装成字典
            processed_chunks.append({
                "category": category_title,  # 技术栈大类
                "title": question_title,  # 面试题目
                "body": question_body  # 正文内容
            })

    # ================= 4. 保存为中间物 =================
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(processed_chunks, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 成功提取出 {len(processed_chunks)} 个独立的面试知识块 -> {os.path.basename(output_filepath)}")


if __name__ == "__main__":
    # 自动定位项目根目录，避免因运行环境导致的路径问题
    # 脚本路径: project/scripts/pipeline/01-clean_split.py -> 往上跳两级到 project/
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_script_dir))

    # 配置路径（匹配您截图中的大写 References）
    INPUT_DIR = os.path.join(project_root, "References")
    OUTPUT_DIR = os.path.join(project_root, "data", "processed")

    # 检查并确保输出目录是一个文件夹
    if os.path.exists(OUTPUT_DIR) and not os.path.isdir(OUTPUT_DIR):
        print(f"⚠️ 发现同名文件 '{OUTPUT_DIR}'，正在清理并转换为文件夹...")
        os.remove(OUTPUT_DIR)

    # 确保输出的 processed 文件夹存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(INPUT_DIR):
        print(f"❌ 找不到输入文件夹: {INPUT_DIR}")
        print("   提示：请确认您的 References 文件夹是否在项目根目录下。")
    else:
        print(f"📂 开始批量处理 '{INPUT_DIR}' 目录下的文件...\n" + "=" * 50)

        # 遍历 References 文件夹下的所有文件
        for filename in os.listdir(INPUT_DIR):
            # 只处理扩展名为 .md 的文件
            if filename.endswith(".md"):
                # 拼接完整的输入文件路径
                input_filepath = os.path.join(INPUT_DIR, filename)

                # 将 .md 后缀替换为 .json，并拼接输出路径
                output_filename = filename.replace(".md", ".json")
                output_filepath = os.path.join(OUTPUT_DIR, output_filename)

                print(f"⏳ 正在处理文件: {filename}")
                process_and_split(input_filepath, output_filepath)

        print("=" * 50 + "\n🎉 所有 Markdown 文件批量清洗切割完毕！")