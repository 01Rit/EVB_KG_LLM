import logging
import json
from typing import Optional
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

COMMUNITY_REPORT_PROMPT = """Given the following community node information, generate a community report:

Node information:
{node_info}

Please return JSON format with:
- title: community title
- summary: brief summary
- findings: list of key findings, each containing summary and explanation"""


class CommunityDetector:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient):
        self.neo4j = neo4j_client
        self.llm = llm_client

    def detect(self) -> list[dict]:
        """Detect communities in the graph."""
        return self.neo4j.detect_communities(level=2)

    def generate_report(self, community: dict) -> dict:
        """Generate LLM report for a community."""
        node_ids = community['nodes']
        nodes_data = self.neo4j.get_subgraph_nodes(node_ids)

        node_info = "\n".join([
            f"- {n.get('props', {}).get('name', n['id'])}"
            for n in nodes_data
        ])

        prompt = COMMUNITY_REPORT_PROMPT.format(node_info=node_info)

        try:
            result = self.llm.generate(prompt)
            import json
            return json.loads(result)
        except Exception as e:
            logger.error(f"Failed to generate community report: {e}")
            return {"title": "Error", "summary": str(e), "findings": []}

    async def generate_all_reports(self, communities: list[dict]) -> list[dict]:
        """Generate reports for all communities."""
        reports = []
        for comm in communities:
            report = self.generate_report(comm)
            report['community_id'] = comm['id']
            report['node_count'] = len(comm['nodes'])
            reports.append(report)
        return reports