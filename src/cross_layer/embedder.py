from typing import Dict, List, Optional
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class CrossLayerEmbedder:
    def __init__(self, milvus_client=None, embedding_model: str = DEFAULT_EMBEDDING_MODEL):
        self.milvus_client = milvus_client
        self.embedding_model = embedding_model
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            from src.utils.llm_client import LLMClient
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def compute_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def build_entity_text(self, name: str, entity_type: str, context: str) -> str:
        return f"{entity_type}: {name}. {context}"

    def recall_candidates(
        self,
        entity_name: str,
        entity_type: str,
        target_layer: str,
        target_relation: str,
        top_k: int = 30,
    ) -> List[Dict]:
        if self.milvus_client is None:
            logger.warning("Milvus client not available, returning empty candidates")
            return []

        entity_text = self.build_entity_text(entity_name, entity_type, "")
        query_vector = self.compute_embedding(entity_text)

        search_results = self.milvus_client.search(
            query_vector=query_vector,
            top_k=top_k
        )

        candidates = []
        for hit in search_results:
            hit_layer = hit.get("layer") or hit.get("type", "").split("_")[0] if "type" in hit else None
            if hit_layer == target_layer:
                candidates.append({
                    "source_name": entity_name,
                    "source_type": entity_type,
                    "target_name": hit.get("text", ""),
                    "target_type": hit.get("type", ""),
                    "target_id": hit.get("id", ""),
                    "score": hit.get("distance", 0.0),
                    "layer": hit_layer,
                })
        return candidates