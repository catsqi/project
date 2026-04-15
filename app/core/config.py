"""
RAG系统配置
"""
import os
from dotenv import load_dotenv
# from dashscope import TextEmbedding

load_dotenv()

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://cats:130151@localhost:5433/cats_interview"
)

# 用于生成embedding

EMBEDDING_API_KEY = os.getenv("DASHSCOPE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL")

# RAG配置
RAG_TOP_K = 3  # 默认检索数量
RAG_SIMILARITY_THRESHOLD = 0.7  # 相似度阈值