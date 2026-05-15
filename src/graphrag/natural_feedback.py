from typing import Optional, AsyncGenerator, Dict, Any, List
import logging
import json

from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.graphrag.web_searcher import WebSearcher
from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph, EvidenceNode

logger = logging.getLogger(__name__)


class NaturalLanguageFeedback:
    """自然语言反馈生成器 - 用于通用问答"""

    PROGRESS_STAGES = [
        ("understanding", "正在理解您的问题..."),
        ("retrieving_local", "正在检索本地知识库..."),
        ("retrieving_web", "正在检索网络资源..."),
        ("ranking", "正在排序证据..."),
        ("generating", "正在生成回答..."),
        ("reasoning", "正在构建推理链..."),
        ("done", "完成"),
    ]

    def __init__(self, retriever: MultiPathRetriever, ranker: EvidenceRanker,
                 llm_client: LLMClient):
        self.retriever = retriever
        self.ranker = ranker
        self.llm = llm_client
        self.web_searcher = WebSearcher()

    async def generate_stream(
        self,
        question: str,
        use_web_search: bool = False,
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
        answer = await self._generate_answer(question, ranked_evidence, web_results)

        yield {"stage": "done", "progress": 1.0, "message": self.PROGRESS_STAGES[5][1], "answer": answer}

    def generate_sync(self, question: str, use_web_search: bool = False) -> Dict[str, Any]:
        """同步生成回答（内部使用）"""
        import asyncio
        return asyncio.run(self.generate_stream(question, use_web_search).__anext__())

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

        # Cross-layer multi-hop traversal: L1 -> L2 (REFERENCE_OF) -> L3 (DEFINITION_OF)
        component_ids = [n.id for n in evidence_graph.nodes if n.node_type == 'Component']
        if component_ids:
            try:
                l2_rows = self.retriever.neo4j.get_l2_by_component_ids(component_ids)
                if l2_rows:
                    l2_ids = [r.get('id', '') for r in l2_rows]
                    l2_evidence = []
                    for r in l2_rows:
                        l2_evidence.append(EvidenceNode(
                            node_type='L2_Entity',
                            id=r.get('id', ''),
                            name=r.get('name', ''),
                            properties=r,
                            text=f"Referenced by {r.get('component_name', '')}: {r.get('name')}, Type: {r.get('entity_type')}, Evidence: {r.get('source_evidence', '')}"
                        ))
                    existing_ids = {n.id for n in evidence_graph.nodes}
                    for node in l2_evidence:
                        if node.id not in existing_ids:
                            evidence_graph.nodes.append(node)
                            existing_ids.add(node.id)
                    logger.info(f'Cross-layer L2: added {len(l2_evidence)} nodes')

                    # Hop 2: L2 -> all neighbors (any relationship type)
                    neighbor_rows = self.retriever.neo4j.get_l2_neighbors(l2_ids)
                    if neighbor_rows:
                        added = 0
                        for r in neighbor_rows:
                            nid = r.get('id', '')
                            if not nid or nid in existing_ids:
                                continue
                            node_labels = r.get('node_labels', []) or []
                            name = r.get('name', '') or ''
                            rel_type = r.get('rel_type', '')
                            entity_name = r.get('entity_name', '')

                            if 'L3_Term' in node_labels or 'Term' in node_labels:
                                node_type = 'Term'
                                tid = nid or r.get('term_id', '')
                                tname = name or r.get('term_id', '')
                                text = f"Defined by {entity_name}: {tname}"
                                if r.get('definition'):
                                    text += f", Definition: {r['definition']}"
                            elif 'L2_Document' in node_labels or 'Document' in node_labels:
                                node_type = 'Document'
                                text = f"Referenced by {entity_name} ({rel_type}): {name}"
                                if r.get('title'):
                                    text += f", Title: {r['title']}"
                            else:
                                node_type = node_labels[0] if node_labels else 'Unknown'
                                text = f"Related to {entity_name} via {rel_type}: {name}"

                            neighbor_node = EvidenceNode(
                                node_type=node_type,
                                id=nid,
                                name=name,
                                properties=r,
                                text=text
                            )
                            evidence_graph.nodes.append(neighbor_node)
                            existing_ids.add(nid)
                            added += 1
                        logger.info(f'Cross-layer neighbors: added {added} nodes')
            except Exception as e:
                logger.warning(f"Cross-layer traversal failed: {e}")

        logger.info(f'Retrieved {len(deduplicated)} nodes for {len(queries)} queries')
        return evidence_graph

    def _extract_battery_model(self, query: str) -> Optional[str]:
        """从查询中提取电池型号 — 先查KG再fallback硬编码"""
        # Query Neo4j for known battery models
        try:
            results = self.retriever.neo4j.execute_query(
                "MATCH (c:Component) WHERE c.battery_model IS NOT NULL RETURN DISTINCT c.battery_model as model LIMIT 50",
                {}
            )
            query_upper = query.upper()
            for r in results:
                model = r.get('model', '')
                if model and model.upper() in query_upper:
                    return model
        except Exception:
            pass

        # Fallback: hardcoded patterns for known models
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
        """从网络检索（DuckDuckGo）"""
        return await self.web_searcher.search(question, top_k=5)

    def _rank_evidence(self, evidence: EvidenceGraph, query: str) -> List[Any]:
        """排序证据"""
        if evidence.nodes:
            return self.ranker.rank(evidence.nodes, query)
        return []

    async def _generate_answer(self, question: str, evidence: List[Any],
                              web_results: List[Dict]) -> str:
        """生成自然语言回答"""

        evidence_parts = []
        for e in evidence[:20]:
            source_type = getattr(e, 'node_type', 'Unknown')
            name = getattr(e, 'name', '')
            text = getattr(e, 'text', '')
            properties = getattr(e, 'properties', {})
            props_str = ', '.join([f"{k}: {v}" for k, v in properties.items() if v is not None and v != ''])
            evidence_parts.append(f"【来源：本地KG-{source_type}:{name}】{text} | 属性: {props_str}")

        web_parts = []
        for r in web_results[:5]:
            title = r.get('title', '')
            snippet = r.get('snippet', '')
            web_parts.append(f"【来源：联网搜索:{title}】{snippet}")

        all_evidence = '\n'.join(evidence_parts + web_parts)

        prompt = f'''任务：回答用户关于电池的问题

用户问题：{question}

相关证据：
{all_evidence if all_evidence else "无相关证据"}

请用自然语言回答用户的问题。
回答要求：
1. 使用中文
2. 每个论点后用()标注来源，格式：【来源：类型:名称】
3. 如果证据不足，说明"根据现有资料无法确定..."
4. 回答要有条理，适当分段
5. 充分利用证据中的所有属性信息（包括但不限于safety_level、tool_required、entity_type等）

回答：'''

        try:
            result = self.llm.generate(prompt)
            return result
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"抱歉，生成回答时出现错误：{str(e)}"
