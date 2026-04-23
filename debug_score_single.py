import sys
sys.path.insert(0, '/app')
from src.allocator.batch_scorer import BatchScorer
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
llm = LLMClient(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    model=settings.llm_model
)

scorer = BatchScorer(llm, neo4j)
result = scorer.score_component('upper housing', 'Audi_A3', '')
print("Score result:")
for k, v in result.items():
    print(f"  {k}: {v}")

neo4j.close()