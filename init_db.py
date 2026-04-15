from app.core.database import db


def init_database():
    print("开始初始化数据库...")

    # 1. 开启 pgvector 扩展
    db.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    print("pgvector 扩展已就绪")

    # 2. 先创建候选人主表
    create_candidates_table = """
    CREATE TABLE IF NOT EXISTS candidates (
        candidate_id UUID PRIMARY KEY,
        candidate_name VARCHAR(100) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    db.execute(create_candidates_table)
    print("candidates 表已就绪")

    # 3. 再创建简历切片表 (1024维，外键依赖上面的 candidates 表)
    create_chunks_table = """
    CREATE TABLE IF NOT EXISTS resume_chunks (
        chunk_id UUID PRIMARY KEY,
        candidate_id UUID REFERENCES candidates(candidate_id) ON DELETE CASCADE,
        chunk_category VARCHAR(50),
        content TEXT NOT NULL,
        metadata JSONB,
        embedding vector(1024),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    db.execute(create_chunks_table)
    print("resume_chunks 表已就绪 (1024维)")

    # 4. 创建 HNSW 向量索引
    create_hnsw_index = """
    CREATE INDEX IF NOT EXISTS idx_resume_chunks_embedding 
    ON resume_chunks USING hnsw (embedding vector_cosine_ops);
    """
    db.execute(create_hnsw_index)
    print("HNSW 向量索引已就绪")

    # 5. 创建 Metadata JSONB 索引
    create_jsonb_index = """
    CREATE INDEX IF NOT EXISTS idx_resume_chunks_metadata 
    ON resume_chunks USING GIN (metadata);
    """
    db.execute(create_jsonb_index)
    print("JSONB 标签过滤索引已就绪")

    print("数据库全部初始化完成！")


if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f" 初始化失败: {e}")