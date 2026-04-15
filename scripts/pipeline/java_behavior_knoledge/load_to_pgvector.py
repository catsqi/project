import os
import json
import psycopg2
import dashscope
from dashscope import TextEmbedding
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

# 1. 加载环境变量 (保持你之前的配置)
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

# 数据库配置 (根据你提供的直接填入或从env读取)
DB_NAME = "cats_interview"
DB_USER = "cats"
DB_PASS = "130151"
DB_PORT = "5433"
DB_HOST = "localhost"
TABLE_NAME = "JavaBackend"  # 存入已存在的表
VECTOR_DIMENSION = 1024


def get_embedding(text):
    """获取向量"""
    try:
        resp = TextEmbedding.call(model=EMBEDDING_MODEL, input=text)
        if resp.status_code == 200:
            return resp.output['embeddings'][0]['embedding']
        return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None


def init_database():
    """连接数据库并初始化"""
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    register_vector(conn)
    return conn, cur


def process_file(file_path, conn, cur):
    """处理单个 JSON 文件并上传"""
    print(f"\n--- 正在处理文件: {os.path.basename(file_path)} ---")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for index, item in enumerate(data):
        item_id = item["id"]
        content = item["content"]
        # 在 metadata 中自动标记来源，方便以后筛选“行为题”
        metadata = item["metadata"]
        metadata["source_file"] = os.path.basename(file_path)
        metadata["type"] = "behavioral"  # 标记为行为题

        metadata_json = json.dumps(metadata, ensure_ascii=False)

        print(f"进度 [{index + 1}/{len(data)}]: {item_id}")
        embedding = get_embedding(content)

        if embedding:
            upsert_query = f"""
                INSERT INTO {TABLE_NAME} (id, content, metadata, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding;
            """
            cur.execute(upsert_query, (item_id, content, metadata_json, embedding))

        # 每 10 条提交一次，防止中途崩溃丢失太多进度
        if (index + 1) % 10 == 0:
            conn.commit()

    conn.commit()
    print(f"文件 {os.path.basename(file_path)} 上传完成。")


def main():
    # 你的文件所在目录
    base_dir = r"D:\大三作业\大三下作业\project\data\output\行为题"
    # 需要处理的文件列表
    target_files = ["行为题1.json", "行为题2.json"]

    conn, cur = init_database()

    try:
        for file_name in target_files:
            full_path = os.path.join(base_dir, file_name)
            if os.path.exists(full_path):
                process_file(full_path, conn, cur)
            else:
                print(f"警告: 找不到文件 {full_path}")
    finally:
        cur.close()
        conn.close()
        print("\n所有任务处理完毕，数据库连接已关闭。")


if __name__ == "__main__":
    main()