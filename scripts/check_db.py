import os
import time
import psycopg2
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_database():
    dbname = os.getenv("POSTGRES_DB", "ai_interview")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = "localhost"
    port = os.getenv("DATABASE_PORT", "5433")

    print(f"正在尝试连接到数据库 '{dbname}' (host: {host})...")
    
    max_retries = 5
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port
            )
            print("Successfully connected to the database!")
            
            cur = conn.cursor()
            
            # 检查并创建 pgvector 扩展
            print("正在检查 pgvector 扩展...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
            
            # 验证扩展是否可用
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            extension = cur.fetchone()
            
            if extension:
                print("✅ pgvector 扩展已就绪！")
                
                # 测试创建一个带有向量列的表
                cur.execute("DROP TABLE IF EXISTS test_vector;")
                cur.execute("CREATE TABLE test_vector (id serial PRIMARY KEY, embedding vector(3));")
                cur.execute("INSERT INTO test_vector (embedding) VALUES ('[1,2,3]'), ('[4,5,6]');")
                cur.execute("SELECT * FROM test_vector ORDER BY embedding <-> '[3,1,2]' LIMIT 1;")
                row = cur.fetchone()
                print(f"✅ 向量搜索测试成功，最接近的行 ID: {row[0]}")
                
            else:
                print("❌ pgvector 扩展未找到。")
                
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"连接失败 (重试 {i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                time.sleep(3)
            else:
                print("❌ 无法连接到数据库。请确保 Docker 容器正在运行。")
                return False

if __name__ == "__main__":
    check_database()
