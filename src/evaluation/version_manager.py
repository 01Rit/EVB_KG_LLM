"""Version management: DesignVersion subgraph creation, retrieval, diff."""
import logging
import uuid
from typing import Optional

from src.evaluation.models import (
    DesignVersion, DesignVersionCreate, DesignVersionDetail, VersionStatus,
)

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages DesignVersion lifecycle and subgraph operations."""

    def __init__(self, neo4j_client):
        self.neo4j = neo4j_client
        self._versions: dict[str, DesignVersion] = {}
        self._subgraphs: dict[str, dict] = {}
        self._counter = 0

    def create_version(self, data: DesignVersionCreate) -> DesignVersion:
        self._counter += 1
        vid = f"v_{uuid.uuid4().hex[:8]}"
        version = DesignVersion(
            version_id=vid,
            design_name=data.design_name,
            version_number=self._counter,
            created_by="user",
            status=VersionStatus.DRAFT,
            component_count=len(data.component_ids),
        )
        self._versions[vid] = version
        self._subgraphs[vid] = self._build_subgraph(
            data.component_ids, data.connection_ids
        )
        logger.info(f"Created DesignVersion {vid} for {data.design_name}")
        return version

    def list_versions(self, design_name: Optional[str] = None) -> list[DesignVersion]:
        versions = list(self._versions.values())
        if design_name:
            versions = [v for v in versions if v.design_name == design_name]
        return sorted(versions, key=lambda v: v.version_number)

    def get_version_detail(self, version_id: str) -> Optional[DesignVersionDetail]:
        version = self._versions.get(version_id)
        if not version:
            return None
        subgraph = self._subgraphs.get(version_id, {"nodes": [], "relationships": []})
        components = [n for n in subgraph["nodes"] if "L1_Component" in n.get("labels", [])]
        connections = [n for n in subgraph["nodes"] if "ConnectionType" in n.get("labels", [])]
        return DesignVersionDetail(
            **version.model_dump(),
            components=components,
            connections=connections,
            relationships=subgraph["relationships"],
        )

    def get_subgraph(self, version_id: str) -> dict:
        return self._subgraphs.get(version_id, {"nodes": [], "relationships": []})

    def update_version_status(self, version_id: str, status: VersionStatus) -> Optional[DesignVersion]:
        version = self._versions.get(version_id)
        if not version:
            return None
        updated = version.model_copy(update={"status": status})
        self._versions[version_id] = updated
        return updated

    def diff_versions(self, v1_id: str, v2_id: str) -> dict:
        """Compare two version subgraphs. Returns {added, removed, modified}."""
        sg1 = self._subgraphs.get(v1_id, {"nodes": [], "relationships": []})
        sg2 = self._subgraphs.get(v2_id, {"nodes": [], "relationships": []})
        ids1 = {n["id"] for n in sg1["nodes"]}
        ids2 = {n["id"] for n in sg2["nodes"]}
        added_nodes = [n for n in sg2["nodes"] if n["id"] not in ids1]
        removed_nodes = [n for n in sg1["nodes"] if n["id"] not in ids2]
        rels1 = {(r["start"], r["end"], r["type"]) for r in sg1["relationships"]}
        rels2 = {(r["start"], r["end"], r["type"]) for r in sg2["relationships"]}
        added_rels = [r for r in sg2["relationships"] if (r["start"], r["end"], r["type"]) not in rels1]
        removed_rels = [r for r in sg1["relationships"] if (r["start"], r["end"], r["type"]) not in rels2]
        return {
            "added": {"nodes": added_nodes, "relationships": added_rels},
            "removed": {"nodes": removed_nodes, "relationships": removed_rels},
            "modified": [],
        }

    def _build_subgraph(self, component_ids: list[str], connection_ids: list[str]) -> dict:
        nodes = []
        relationships = []
        for cid in component_ids:
            nodes.append({"id": cid, "labels": ["L1_Component"], "name": cid})
        for cid in connection_ids:
            nodes.append({"id": cid, "labels": ["ConnectionType"], "name": cid})
        # Create USES_CONNECTION from each component to each connection
        for comp_id in component_ids:
            for conn_id in connection_ids:
                relationships.append({"start": comp_id, "end": conn_id, "type": "USES_CONNECTION"})
        return {"nodes": nodes, "relationships": relationships}
