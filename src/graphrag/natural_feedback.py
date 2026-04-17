from typing import Optional, AsyncGenerator, Dict, Any, List
import logging
import json

from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph

logger = logging.getLogger(__name__)


class NaturalLanguageFeedback:
    """自然语言反馈生成器 - 用于通用问答"""

    PROGRESS_STAGES = [
        ("understanding", "正在理解您的问题..."),
        ("retrieving_local", "正在检索本地知识库..."),
        ("retrieving_web", "正在检索网络资源..."),
        ("ranking", "正在排序证据..."),
        ("generating", "正在生成回答..."),
        ("done", "完成"),
    ]

    def __init__(self, retriever: MultiPathRetriever, ranker: EvidenceRanker,
                 llm_client: LLMClient):
        self.retriever = retriever
        self.ranker = ranker
        self.llm = llm_client

    async def generate_stream(
        self,
        question: str,
        use_web_search: bool = False,
        context: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """SSE流式生成回答"""

        yield {"stage": "understanding", "progress": 0.1, "message": self.PROGRESS_STAGES[0][1]}
        rewritten_queries = self._rewrite_query(question)

        yield {"stage": "retrieving_local", "progress": 0.3, "message": self.PROGRESS_STAGES[1][1]}
        evidence_graph = await self._retrieve_local(rewritten_queries)

        if use_web_search:
            yield {"stage": "retrieving_web", "progress": 0.5, "message": self.PROGRESS_STAGES[2][1]}
            web_results = await self._retrieve_web(question)
        else:
            web_results = []

        yield {"stage": "ranking", "progress": 0.6, "message": self.PROGRESS_STAGES[3][1]}
        ranked_evidence = self._rank_evidence(evidence_graph, question)

        yield {"stage": "generating", "progress": 0.8, "message": self.PROGRESS_STAGES[4][1]}
        answer = await self._generate_answer(question, ranked_evidence, web_results, context)

        yield {"stage": "done", "progress": 1.0, "message": self.PROGRESS_STAGES[5][1], "answer": answer}

    def generate_sync(self, question: str, use_web_search: bool = False,
                     context: Optional[List[str]] = None) -> Dict[str, Any]:
        """同步生成回答（内部使用）"""
        import asyncio
        return asyncio.run(self.generate_stream(question, use_web_search, context).__anext__())

    def _rewrite_query(self, question: str) -> List[str]:
        """重写查询为多个子查询"""
        return [question]

    async def _retrieve_local(self, queries: List[str], battery_model: str = None) -> EvidenceGraph:
        """从本地知识图谱检索"""
        all_nodes = []

        for query in queries:
            extracted_model = battery_model or self._extract_battery_model(query)

            if extracted_model:
                model_nodes = self.retriever.get_all_components(extracted_model, top_k=30)
                all_nodes.extend(model_nodes)

            component_nodes = self.retriever._retrieve_components(query, top_k=30)
            document_nodes = self.retriever._retrieve_documents(query, top_k=30)
            term_nodes = self.retriever._retrieve_terms(query, top_k=30)

            all_nodes.extend(component_nodes)
            all_nodes.extend(document_nodes)
            all_nodes.extend(term_nodes)

        deduplicated = self._deduplicate_nodes(all_nodes, top_k=30)

        subgraph = self.retriever.neo4j.get_subgraph([n.id for n in deduplicated], depth=2)
        evidence_graph = EvidenceGraph(nodes=deduplicated, edges=subgraph.get('edges', []))

        logger.info(f'Retrieved {len(deduplicated)} nodes for {len(queries)} queries')
        return evidence_graph

    def _extract_battery_model(self, query: str) -> Optional[str]:
        """从查询中提取电池型号"""
        import re

        query_upper = query.upper()

        if 'AUDI' in query_upper and 'A3' in query_upper:
            return 'Audi_A3'
        if 'TESLA' in query_upper and 'MODEL' in query_upper:
            return 'Tesla_Model_3'
        if 'BMW' in query_upper:
            match = re.search(r'BMW[A-Z]\d{2,4}', query_upper.replace(' ', ''))
            if match:
                return match.group(0)
        if 'NIO' in query_upper and 'ES' in query_upper:
            match = re.search(r'ES\d+', query_upper)
            if match:
                return 'NIO_' + match.group(0)

        return None

    def _deduplicate_nodes(self, nodes: list, top_k: int = 30) -> list:
        seen = {}
        for node in nodes:
            if node.id not in seen:
                seen[node.id] = node
        return list(seen.values())[:top_k]

    async def _retrieve_web(self, question: str) -> List[Dict]:
        """从网络检索"""
        return []

    def _rank_evidence(self, evidence: EvidenceGraph, query: str) -> List[Any]:
        """排序证据"""
        if evidence.nodes:
            return self.ranker.rank(evidence.nodes, query)
        return []

    async def _generate_answer(self, question: str, evidence: List[Any],
                              web_results: List[Dict],
                              context: Optional[List[str]]) -> str:
        """生成自然语言回答"""
        context_str = ', '.join(context) if context else '无'

        evidence_parts = []
        for e in evidence[:10]:
            source_type = getattr(e, 'node_type', 'Unknown')
            name = getattr(e, 'name', '')
            text = getattr(e, 'text', '')
            evidence_parts.append(f"【来源：本地KG-{source_type}:{name}】{text}")

        web_parts = []
        for r in web_results[:5]:
            title = r.get('title', '')
            snippet = r.get('snippet', '')
            web_parts.append(f"【来源：联网搜索:{title}】{snippet}")

        all_evidence = '\n'.join(evidence_parts + web_parts)

        prompt = f'''任务：回答用户关于电池的问题

用户问题：{question}
上下文：{context_str}

相关证据：
{all_evidence if all_evidence else "无相关证据"}

请用自然语言回答用户的问题。
回答要求：
1. 使用中文
2. 每个论点后用()标注来源，格式：【来源：类型:名称】
3. 如果证据不足，说明"根据现有资料无法确定..."
4. 回答要有条理，适当分段

回答：'''

        try:
            result = self.llm.generate(prompt)
            return result
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"抱歉，生成回答时出现错误：{str(e)}"
