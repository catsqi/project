import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# ================= 1. 加载环境变量与初始化 =================
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError("未能在环境变量中找到 DEEPSEEK_API_KEY，请检查 .env 文件！")

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)


# ================= 2. 核心大模型抽取逻辑 =================
def extract_metadata_with_llm(chunk, source_filename):
    """
    向 DeepSeek 发送请求，将切分好的文本块转化为标准 JSON 格式
    """
    # 【核心升级】：高度完善的 System Prompt，严格约束输出格式与字段含义
    system_prompt = """
    你是一个专业的技术面试知识库构建引擎。你的任务是将用户提供的非结构化面试文本提炼为结构化的 JSON 元数据，供“数字人面试官”系统作为底层题库和打分依据。

    请严格按照以下 JSON 格式输出，绝不能改变键名（Key），不要输出任何多余的解释文字，也不要带有 ```json 这样的 Markdown 标记。直接返回纯 JSON 字符串。

    【目标 JSON 格式与字段生成规则】：
    {
      "id": "根据技术栈和题意生成唯一的全英文小写标识，如 java_basis_oop_001",
      "content": "用 50-80 字精简概括核心理论答案。必须完全忽略并剔除具体的代码块、示例和图表脚本，只保留知识点精华。",
      "metadata": {
        "category_stack": "根据大类上下文，推断出最具体的单个技术栈标签，例如：Java基础、JVM、MySQL、并发编程 等。",
        "interview_point": "将面试题标题润色为面试官向候选人提问时的口语化完整句子。",
        "best_answer_model": {
          "logic_chain": "提炼高质量回答的逻辑递进路径，使用 -> 连接，例如：底层数据结构 -> 扩容机制 -> 线程安全分析",
          "scoring_keywords": [
            "提取 4-6 个最核心的专业名词或短语（不超过 6 个字）",
            "用于后续自动化打分系统的关键词匹配"
          ]
        },
        "source_ref": "严格替换为用户传入的源文件名"
      }
    }
    """

    user_prompt = f"源文件名: {source_filename}\n大类上下文: {chunk.get('category')}\n面试题标题: {chunk.get('title')}\n详细内容: {chunk.get('body')}\n\n请提取并生成 JSON。"

    # 调用大模型
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1  # 保持极低温度，防止格式发散
    )

    raw_result = response.choices[0].message.content.strip()

    # 健壮性兜底：清理可能存在的 Markdown 格式符
    if raw_result.startswith("```json"):
        raw_result = raw_result[7:]
    if raw_result.endswith("```"):
        raw_result = raw_result[:-3]

    return json.loads(raw_result.strip())


# ================= 3. 批量处理与文件 I/O 逻辑 =================
def process_all_files(input_dir, output_dir):
    """
    遍历 data/processed 目录，处理所有 JSON 并一一对应保存至 data/output
    """
    os.makedirs(output_dir, exist_ok=True)

    # 找出所有待处理的 json 文件
    files_to_process = [f for f in os.listdir(input_dir) if f.endswith(".json")]

    if not files_to_process:
        print(f"在 '{input_dir}' 下没有找到 .json 中间物文件。")
        return

    print(f"发现 {len(files_to_process)} 个待处理文件，开始启动 LLM 批量语义抽取...\n" + "=" * 60)

    for filename in files_to_process:
        input_filepath = os.path.join(input_dir, filename)
        output_filepath = os.path.join(output_dir, filename)

        print(f"\n正在处理文件: {filename}")

        # 读取中间物
        with open(input_filepath, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        final_metadata_list = []

        # 将原始的 Markdown 文件名传给大模型做 source_ref
        source_doc_name = filename.replace(".json", ".md")

        for idx, chunk in enumerate(chunks):
            print(f"[题目 {idx + 1}/{len(chunks)}] 正在呼叫 DeepSeek: {chunk['title']}")
            try:
                # 核心提取步骤
                metadata = extract_metadata_with_llm(chunk, source_doc_name)
                final_metadata_list.append(metadata)
            except Exception as e:
                print(f"抽取失败 '{chunk['title']}': {e}")

        # 一一对应写入到 data/output 文件夹
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(final_metadata_list, f, ensure_ascii=False, indent=2)

        print(f"文件 {filename} 处理完毕！结果已存入 -> {output_dir}")


if __name__ == "__main__":
    # 动态获取项目根目录
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_script_dir))

    # 精确设定输入目录 (processed) 和 输出目录 (output)
    INPUT_DIR = os.path.join(project_root, "data", "processed")
    OUTPUT_DIR = os.path.join(project_root, "data", "output")

    if not os.path.exists(INPUT_DIR):
        print(f"找不到输入文件夹 '{INPUT_DIR}'，请确认已先运行切割脚本！")
    else:
        process_all_files(INPUT_DIR, OUTPUT_DIR)
        print("\n" + "=" * 60 + "\n🎉 全量大模型结构化抽取完毕！终态数据已准备就绪，可以随时灌入向量数据库。")