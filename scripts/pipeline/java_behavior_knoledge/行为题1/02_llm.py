import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)


def generate_star_json(raw_item):
    system_prompt = """你是一个资深的人力资源专家和 AI 数据架构师。你的任务是将非结构化的行为面试题转化为严格的 JSON 数据。
请严格遵守以下规则：
1. 仔细阅读题目及追问，提炼其核心考察重点 (interview_point)。
2. 必须按照 STAR 原则（Situation, Task, Action, Result）生成详细的评分判断问句（star_scoring_criteria）。
3. id 字段请根据题目含义生成一个简短的英文标识（如 beh_client_01）。
4. 必须输出合法的 JSON 格式，绝不能包含任何 Markdown 格式或解释性文字。"""

    user_prompt = f"""能力维度：{raw_item['category']}
题目原文：{raw_item['raw_content']}

请根据以上信息生成 JSON，严格遵循以下结构（注意保留 source_ref 和 type）：
{{
  "id": "...",
  "content": "{raw_item['raw_content'].split('追问')[0].strip()}", 
  "metadata": {{
    "category": "{raw_item['category']}",
    "interview_point": "...",
    "best_answer_model": {{
      "star_scoring_criteria": {{
        "Situation": "...",
        "Task": "...",
        "Action": "...",
        "Result": "..."
      }}
    }},
    "source_ref": "{raw_item['source_ref']}",
    "type": "behavioral"
  }}
}}"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    result_str = response.choices[0].message.content
    return json.loads(result_str)


if __name__ == "__main__":
    PROJECT_ROOT = r"D:\大三作业\大三下作业\project"
    input_file = r"D:\大三作业\大三下作业\project\data\processed\行为题\行为题1.json"
    output_file = os.path.join(PROJECT_ROOT, "data", "output", "行为题", "行为题2.json")
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    final_dataset = []

    print(f"开始调用大模型处理，本次共处理 {len(raw_data)} 道题目...")

    for i, item in enumerate(raw_data, 1):
        print(f"正在处理第 {i}/{len(raw_data)} 题: {item['category']}...")
        processed_json = generate_star_json(item)
        if processed_json:
            final_dataset.append(processed_json)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)

    print(f"处理完毕！最终数据已保存至: {output_file}")