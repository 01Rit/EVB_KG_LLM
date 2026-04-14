import sys
sys.path.insert(0, r'D:\/KG_project\/Final4.14')
from src.kg.client import Neo4jClient, MilvusClient
from src.kg.models import Component, Document, Term, EvidenceNode, EvidenceGraph
print('All imports OK - Test passed')