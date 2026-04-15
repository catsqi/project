import os
import json
import psycopg2
import dashscope
from dashscope import TextEmbedding
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

# 1. 加载环境变量
load_dotenv()

# 阿里云 DashScope 配置
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

# PostgreSQL 配置
DB_NAME = os.getenv("POSTGRES_DB", "cats_interview")
DB_USER = os.getenv("POSTGRES_USER", "cats")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "130151")
DB_PORT = os.getenv("DATABASE_PORT", "5433")
DB_HOST = "localhost"

# 全能表名
TABLE_NAME = os.getenv("VECTOR_DB_COLLECTION", "JavaBackend")

# text-embedding-v3 输出维度为 1024
VECTOR_DIMENSION = 1024


def get_embedding(text):
    """调用阿里云 API 将文本转换为向量"""
    try:
        resp = TextEmbedding.call(
            model=EMBEDDING_MODEL,
            input=text
        )
        if resp.status_code == 200:
            return resp.output['embeddings'][0]['embedding']
        else:
            print(f"API 调用失败: {resp.message}")
            return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None


def init_database():
    """连接数据库并初始化表结构"""
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()

    # 确保开启向量插件
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 创建全能表 JavaBackend
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id VARCHAR(100) PRIMARY KEY,
            content TEXT NOT NULL,
            metadata JSONB NOT NULL,
            embedding VECTOR({VECTOR_DIMENSION})
        );
    """)
    conn.commit()
    register_vector(conn)
    return conn, cur


def main():
    # JSON 文件路径
    json_path = r"/knowledge/Java后端知识库/Java技术知识.json"

    if not os.path.exists(json_path):
        print(f"找不到文件: {json_path}")
        return

    # 加载 JSON 数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 初始化数据库
    conn, cur = init_database()
    print(f"连接数据库成功: {DB_NAME}, 准备写入表: {TABLE_NAME}")

    for index, item in enumerate(data):
        item_id = item["id"]
        content = item["content"]
        metadata_json = json.dumps(item["metadata"], ensure_ascii=False)

        print(f"处理中 [{index + 1}/{len(data)}]: {item_id}")
        embedding = get_embedding(content)

        if embedding:
            # 增量更新逻辑
            upsert_query = f"""
                INSERT INTO {TABLE_NAME} (id, content, metadata, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding;
            """
            cur.execute(upsert_query, (item_id, content, metadata_json, embedding))

        if (index + 1) % 10 == 0:
            conn.commit()

    conn.commit()
    cur.close()
    conn.close()
    print(f"处理完成，数据已存入数据库 {DB_NAME} 的 {TABLE_NAME} 表。")


if __name__ == "__main__":
    main()