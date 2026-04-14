import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.kg.client import Neo4jClient, MilvusClient


def test_neo4j_client_import():
    assert Neo4jClient is not None


def test_milvus_client_import():
    assert MilvusClient is not None