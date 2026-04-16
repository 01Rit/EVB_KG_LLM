import asyncio
import json
from typing import Optional
import logging
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
from src.utils.tokenizer import truncate_by_token_size
from src.graphrag.community import CommunityDetector

logger = logging.getLogger(__name__)

MAP_PROMPT = """Given the following community reports, extract key points related to the query:

Query: {query}

Community reports:
{community_reports}

Please return JSON with points array, each containing:
- description: key point description
- score: importance score (0-1)"""

REDUCE_PROMPT = """Given the following key points, generate a final response:

Query: {query}

Key points:
{points}

Generate a comprehensive summary of all key points."""

MAX_COMMUNITY_TOKENS = 8000
MAX_POINTS_TOKENS = 6000


class GlobalQueryEngine:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient,
                 community_detector: Optional[CommunityDetector] = None):
        self.neo4j = neo4j_client
        self.llm = llm_client
        self.community_detector = community_detector or CommunityDetector(neo4j_client, llm_client)

    def query(self, query: str, max_communities: int = 50) -> dict:
        """Execute global query using Map-Reduce pattern."""
        communities = self.community_detector.detect()
        if not communities:
            return {'response': 'No communities found', 'error': None}

        communities = truncate_by_token_size(
            communities,
            key=lambda c: str(c['nodes'][:10]),
            max_token_size=MAX_COMMUNITY_TOKENS
        )[:max_communities]

        try:
            try:
                loop = asyncio.get_running_loop()
                raise RuntimeError("Cannot run async in sync context with running loop")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                reports = loop.run_until_complete(
                    self.community_detector.generate_all_reports(communities)
                )
                loop.close()
        except Exception as e:
            logger.error(f"Failed to generate community reports: {e}")
            return {'response': f'Error: {e}', 'error': str(e)}

        map_results = self._map_phase(query, reports)
        response = self._reduce_phase(query, map_results)

        return {'response': response, 'error': None}

    def _map_phase(self, query: str, reports: list[dict]) -> list[dict]:
        """Map: Extract key points from each community report."""
        batch = []
        all_points = []

        for report in reports:
            report_str = f"## {report.get('title', 'N/A')}\n{report.get('summary', '')}"
            batch.append(report_str)

            if len("\n---\n".join(batch)) > MAX_COMMUNITY_TOKENS // 2:
                points = self._extract_points_from_batch(query, batch)
                all_points.extend(points)
                batch = []

        if batch:
            points = self._extract_points_from_batch(query, batch)
            all_points.extend(points)

        all_points = [p for p in all_points if p.get('score', 0) > 0]
        all_points.sort(key=lambda x: x.get('score', 0), reverse=True)
        return all_points

    def _extract_points_from_batch(self, query: str, batch: list[str]) -> list[dict]:
        """Extract key points from a batch of community reports."""
        community_reports = "\n---\n".join(batch)
        prompt = MAP_PROMPT.format(query=query, community_reports=community_reports)

        try:
            result = self.llm.generate(prompt)
            import json
            data = json.loads(result)
            return data.get('points', [])
        except Exception as e:
            logger.error(f"Map phase failed: {e}")
            return []

    def _reduce_phase(self, query: str, points: list[dict]) -> str:
        """Reduce: Merge and generate final response."""
        if not points:
            return "No relevant information found."

        points = truncate_by_token_size(
            points,
            key=lambda p: p.get('description', ''),
            max_token_size=MAX_POINTS_TOKENS
        )

        points_str = "\n".join([
            f"- {p.get('description', '')} (score: {p.get('score', 0)})"
            for p in points
        ])

        prompt = REDUCE_PROMPT.format(query=query, points=points_str)

        try:
            return self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"Reduce phase failed: {e}")
            return f"Error generating response: {e}"