import os
import asyncpg
from typing import List, Dict
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pgvector.asyncpg import register_vector

load_dotenv()


class PostgresRetriever:
    """
    基于 PostgreSQL + pgvector 的题库检索器
    """

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.embed_client = AsyncOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("EMBEDDING_BASE_URL")
        )
        self.embed_model = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
        print(f"[Retriever] 初始化完成，模型: {self.embed_model}")

    async def get_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            return []
        try:
            response = await self.embed_client.embeddings.create(
                input=text[:1000],
                model=self.embed_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[Retriever Error] Embedding 失败: {e}")
            return []

    async def search_questions(
            self,
            query: str,
            category: str = None,
            limit: int = 3
    ) -> List[Dict]:
        query_vector = await self.get_embedding(query)
        if not query_vector:
            print("[Retriever] 获取向量失败，返回空结果")
            return []

        print(f"[RAG] 检索: '{query[:30]}...'")

        # 基础 SQL：只包含 SELECT 和 FROM，不包含 ORDER BY 和 LIMIT
        sql = """
            SELECT 
                id,
                metadata->>'interview_point' as question,
                metadata->>'category_stack' as category,
                content,
                1 - (embedding <=> $1) as similarity
            FROM "javabackend" 
            WHERE 1=1
        """
        params = [query_vector]

        # 动态拼接类别筛选条件
        if category:
            sql += f" AND metadata->>'category_stack' = ${len(params) + 1}"
            params.append(category)

        # 最后统一拼接 ORDER BY 和 LIMIT（只出现一次）
        sql += f" ORDER BY embedding <=> $1 LIMIT ${len(params) + 1}"
        params.append(limit)

        conn = None
        try:
            conn = await asyncpg.connect(self.db_url)
            await register_vector(conn)
            rows = await conn.fetch(sql, *params)

            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "question": row["question"],
                    "category": row["category"],
                    "content": row["content"],
                    "similarity": float(row["similarity"])
                })

            print(f"[RAG] 命中 {len(results)} 题")
            for i, r in enumerate(results, 1):
                print(f"  {i}. [{r['category']}] {r['question'][:50]}... (相似度: {r['similarity']:.3f})")

            return results

        except Exception as e:
            print(f"[Database Error] 检索失败: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def get_question_by_id(self, question_id: str) -> Dict:
        try:
            conn = await asyncpg.connect(self.db_url)
            await register_vector(conn)
            row = await conn.fetchrow(
                'SELECT id, content, metadata FROM "javabackend" WHERE id = $1',
                question_id
            )
            await conn.close()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"[Database Error] 查询失败: {e}")
            return None

    async def search_resume_chunks(
            self,
            candidate_id: str,
            query: str,
            chunk_type: str = None,
            top_k: int = 3
    ) -> List[Dict]:
        query_vector = await self.get_embedding(query)
        if not query_vector:
            print("[Resume RAG] 获取向量失败，返回空结果")
            return []

        print(f"[Resume RAG] 检索候选人 {candidate_id[:8]}... 的简历: '{query[:30]}...'")

        sql = """
            SELECT 
                chunk_id,
                chunk_category,
                content,
                metadata,
                1 - (embedding <=> $1) as similarity
            FROM resume_chunks
            WHERE candidate_id = $2
        """
        params = [query_vector, candidate_id]

        if chunk_type:
            sql += f" AND chunk_category = ${len(params) + 1}"
            params.append(chunk_type)

        sql += f" ORDER BY embedding <=> $1 LIMIT ${len(params) + 1}"
        params.append(top_k)

        conn = None
        try:
            conn = await asyncpg.connect(self.db_url)
            await register_vector(conn)
            rows = await conn.fetch(sql, *params)

            results = []
            for row in rows:
                results.append({
                    "chunk_id": str(row["chunk_id"]),
                    "chunk_category": row["chunk_category"],
                    "content": row["content"],
                    "metadata": row["metadata"] or {},
                    "similarity": float(row["similarity"])
                })

            print(f"[Resume RAG] 命中 {len(results)} 个切片")
            for i, r in enumerate(results, 1):
                print(f"  {i}. [{r['chunk_category']}] {r['content'][:40]}... (相似度: {r['similarity']:.3f})")

            return results

        except Exception as e:
            print(f"[Database Error] 简历检索失败: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def get_resume_context(
            self,
            candidate_id: str,
            topic: str,
            max_chunks: int = 2
    ) -> str:
        chunks = await self.search_resume_chunks(
            candidate_id=candidate_id,
            query=topic,
            top_k=max_chunks
        )
        if not chunks:
            return ""
        context_parts = ["【候选人简历相关内容】"]
        for chunk in chunks:
            context_parts.append(f"- {chunk['content']}")
        return "\n".join(context_parts)


_retriever_instance = None


def get_retriever() -> PostgresRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = PostgresRetriever()
    return _retriever_instance