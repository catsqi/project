"""
回答质量分析器

职责：
- 快速分析用户回答质量（本地规则，不调用 LLM）
- 识别逃避、模糊、优秀等不同质量等级
"""

import re
from .models import AnswerQuality


class AnswerQualityAnalyzer:
    """回答质量分析器"""
    
    # 逃避关键词
    EVASION_KEYWORDS = [
        "不会", "没用过", "不了解", "忘了", "不清楚",
        "不熟悉", "没有经验", "没接触过", "不太懂"
    ]
    
    # 细节指标词
    DETAIL_INDICATORS = [
        "比如", "例如", "我们项目", "当时", "结果",
        "提升了", "降低了", "优化了", "解决了", "实现了",
        "设计了", "开发了", "维护了", "重构了"
    ]
    
    # 数据指标词
    DATA_INDICATORS = [
        "qps", "tps", "ms", "秒", "分钟", "%", "倍",
        "万", "百万", "千万", "gb", "mb", "kb"
    ]
    
    def analyze(self, user_input: str) -> tuple[AnswerQuality, str]:
        """
        分析回答质量
        
        返回: (质量等级, 判断依据)，用于决策分支
        """
        text = user_input.strip().lower()
        
        # 1. 检测逃避
        if self._has_evasion(text):
            return AnswerQuality.EVASIVE, "检测到逃避关键词"
        
        # 2. 检测过短且无技术词
        if self._is_vague(text, user_input):
            return AnswerQuality.VAGUE, "回答过短或缺乏技术术语"
        
        # 3. 检测优秀
        if self._is_excellent(text, user_input):
            return AnswerQuality.EXCELLENT, "回答详细，包含具体案例或数据指标"
        
        # 4. 默认合格
        return AnswerQuality.ADEQUATE, "回答基本合格，有技术内容"
    
    def _has_evasion(self, text: str) -> bool:
        """检测是否有逃避关键词"""
        return any(kw in text for kw in self.EVASION_KEYWORDS)
    
    def _is_vague(self, text: str, original: str) -> bool:
        """检测是否过于模糊"""
        has_tech_term = bool(re.search(r'[a-z]+', text))
        return len(original) < 30 and not has_tech_term
    
    def _is_excellent(self, text: str, original: str) -> bool:
        """检测是否优秀回答"""
        detail_count = sum(1 for ind in self.DETAIL_INDICATORS if ind in text)
        has_data = any(ind in text for ind in self.DATA_INDICATORS)
        
        return (detail_count >= 2 or has_data) and len(original) > 80
    
    def extract_tech_keywords(self, text: str) -> list:
        """提取技术关键词"""
        tech_terms = [
            "redis", "mysql", "kafka", "微服务", "分布式", "高并发",
            "缓存", "索引", "事务", "锁", "线程池", "docker", "k8s",
            "spring", "java", "python", "go", "nginx", "elasticsearch"
        ]
        
        text_lower = text.lower()
        found = [term for term in tech_terms if term in text_lower]
        return found
