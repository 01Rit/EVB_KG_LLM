import re
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

ALIAS_DICTIONARY = {
    'battery module': 'battery pack module',
    'battery pack module': 'battery module',
    'module': '模组',
    '模组': 'module',
    'cell': '电芯',
    '电芯': 'cell',
    'battery cover': '电池盖板',
    '电池盖板': 'battery cover',
    'cover': '电池盖',
    '电池盖': 'battery cover',
    '高压连接器': 'HV connector',
    'HV connector': '高压连接器',
    'connector': '连接器',
    '连接器': 'connector',
    '冷却板': 'cooling plate',
    'cooling plate': '冷却板',
    'screw': '螺丝',
    '螺丝': 'screw',
    '螺栓': 'bolt',
    'bolt': '螺栓',
    '扭矩扳手': 'torque wrench',
    'torque wrench': '扭矩扳手',
    '绝缘': 'insulation',
    'insulation': '绝缘',
    'pack': '电池包',
    '电池包': 'pack',
}


def normalize_name(name: str) -> str:
    if not name:
        return ''
    n = name.lower().strip()
    n = re.sub(r'[\s\-_]+', '', n)
    return n


def build_alias_sets() -> Dict[str, Set[str]]:
    alias_map: Dict[str, Set[str]] = {}
    for k, v in ALIAS_DICTIONARY.items():
        norm_k = normalize_name(k)
        norm_v = normalize_name(v)
        if norm_k not in alias_map:
            alias_map[norm_k] = set()
        if norm_v not in alias_map:
            alias_map[norm_v] = set()
        alias_map[norm_k].add(norm_v)
        alias_map[norm_v].add(norm_k)
    return alias_map


def are_aliases(name1: str, name2: str, alias_sets: Dict[str, Set[str]]) -> bool:
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    if n1 == n2:
        return True
    if n1 in alias_sets and n2 in alias_sets[n1]:
        return True
    if n2 in alias_sets and n1 in alias_sets[n2]:
        return True
    return False


def names_match(name1: str, name2: str) -> bool:
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    if n1 == n2:
        return True
    if n1 in n2 or n2 in n1:
        return True
    return False


def entity_type_compatible(t1: str, t2: str) -> bool:
    compatible_groups = [
        {'component', 'part', 'module', 'cell', 'pack', 'cover', 'plate', 'connector', 'terminal'},
        {'tool', 'wrench', 'screwdriver', 'driver', 'fixture'},
        {'action', 'process', 'operation'},
        {'parameter', 'value', 'spec'},
        {'safety', 'warning', 'precaution'},
    ]
    t1_lower = t1.lower()
    t2_lower = t2.lower()
    for group in compatible_groups:
        if t1_lower in group and t2_lower in group:
            return True
    return t1_lower == t2_lower


def definition_keywords_in_text(text: str) -> bool:
    keywords = ['is a', 'refers to', 'defined as', 'definition of', 'means', 'is defined', 'represent', 'denote']
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def generate_run_id() -> str:
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    counter = int(now.strftime('%H%M'))
    return f"{date_str}_{counter:03d}"


class CrossLayerBatchBuilder:
    def __init__(self, neo4j_client, milvus_client=None, llm_client=None):
        self.neo4j = neo4j_client
        self.milvus = milvus_client
        self.llm = llm_client
        self.alias_sets = build_alias_sets()
        self.run_id = generate_run_id()

    def build_all(self) -> Dict:
        l1_components = self._get_l1_components()
        l2_entities = self._get_l2_entities()
        l3_terms = self._get_l3_terms()

        ref_count = self._build_reference_of(l1_components, l2_entities)
        def_count = self._build_definition_of(l2_entities, l3_terms)

        integrity = self._check_integrity(l1_components, l2_entities)

        return {
            'run_id': self.run_id,
            'reference_of_created': ref_count,
            'definition_of_created': def_count,
            'integrity': integrity,
        }

    def _get_l1_components(self) -> List[Dict]:
        results = self.neo4j.execute_query(
            'MATCH (c:Component) RETURN c.id as id, c.name as name'
        )
        if not results:
            return []
        return [{'id': r.get('id', ''), 'name': r.get('name', '')} for r in results]

    def _get_l2_entities(self) -> List[Dict]:
        results = self.neo4j.execute_query(
            'MATCH (e:L2_Entity) RETURN e.id as id, e.name as name, e.entity_type as entity_type, e.source_evidence as source_evidence'
        )
        if not results:
            return []
        return [
            {
                'id': r.get('id', ''),
                'name': r.get('name', ''),
                'entity_type': r.get('entity_type', 'component'),
                'source_evidence': r.get('source_evidence', ''),
            }
            for r in results
        ]

    def _get_l3_terms(self) -> List[Dict]:
        results = self.neo4j.execute_query(
            'MATCH (t:L3_Term) RETURN t.id as id, t.name as name, t.definition as definition'
        )
        if not results:
            return []
        return [
            {
                'id': r.get('id', ''),
                'name': r.get('name', ''),
                'definition': r.get('definition', ''),
            }
            for r in results
        ]

    def _build_reference_of(self, l1_components: List[Dict], l2_entities: List[Dict]) -> int:
        K = 5
        created = 0

        for l1 in l1_components:
            matches = []
            for l2 in l2_entities:
                source = None
                if names_match(l1['name'], l2['name']):
                    source = 'name_match'
                elif are_aliases(l1['name'], l2['name'], self.alias_sets):
                    source = 'alias'
                elif entity_type_compatible(l1.get('name', ''), l2.get('entity_type', '')):
                    if names_match(l1['name'], l2.get('entity_type', '')):
                        source = 'type_hint'

                if source:
                    matches.append({
                        'source_name': l1['name'],
                        'target_id': l2['id'],
                        'confidence': 0.9,
                        'source': source,
                    })

            matches.sort(key=lambda x: x['confidence'], reverse=True)
            matches = matches[:K]

            for m in matches:
                cypher = '''
                MATCH (a:Component {name: $source_name})
                MATCH (b:L2_Entity {id: $target_id})
                MERGE (a)-[r:REFERENCE_OF]->(b)
                ON CREATE SET r.confidence = $confidence, r.run_id = $run_id, r.source = $source
                ON MATCH SET r.confidence = CASE WHEN r.confidence < $confidence THEN $confidence ELSE r.confidence END
                '''
                try:
                    self.neo4j.execute_query(cypher, {
                        'source_name': m['source_name'],
                        'target_id': m['target_id'],
                        'confidence': m['confidence'],
                        'run_id': self.run_id,
                        'source': m['source'],
                    })
                    created += 1
                except Exception as e:
                    logger.warning(f"Failed to create REFERENCE_OF: {e}")

        logger.info(f"Created {created} REFERENCE_OF edges")
        return created

    def _build_definition_of(self, l2_entities: List[Dict], l3_terms: List[Dict]) -> int:
        K = 3
        SIMILARITY_THRESHOLD = 0.75
        created = 0

        for l2 in l2_entities:
            matches = []
            for l3 in l3_terms:
                source = None
                confidence = 0.75

                if names_match(l2['name'], l3['name']):
                    source = 'name_match'
                    confidence = 0.85
                elif definition_keywords_in_text(l2.get('source_evidence', '')) and names_match(l2['name'], l3['name']):
                    source = 'keyword_detection'
                    confidence = 0.80
                elif self.milvus:
                    try:
                        sim = self._get_embedding_similarity(l2['name'], l3['name'])
                        if sim > SIMILARITY_THRESHOLD:
                            source = 'embedding'
                            confidence = sim
                    except Exception:
                        pass

                if source:
                    matches.append({
                        'source_id': l2['id'],
                        'target_id': l3['id'],
                        'confidence': confidence,
                        'source': source,
                    })

            matches.sort(key=lambda x: x['confidence'], reverse=True)
            matches = matches[:K]

            for m in matches:
                cypher = '''
                MATCH (a:L2_Entity {id: $source_id})
                MATCH (b:L3_Term {id: $target_id})
                MERGE (a)-[r:DEFINITION_OF]->(b)
                ON CREATE SET r.confidence = $confidence, r.run_id = $run_id, r.source = $source
                ON MATCH SET r.confidence = CASE WHEN r.confidence < $confidence THEN $confidence ELSE r.confidence END
                '''
                try:
                    self.neo4j.execute_query(cypher, {
                        'source_id': m['source_id'],
                        'target_id': m['target_id'],
                        'confidence': m['confidence'],
                        'run_id': self.run_id,
                        'source': m['source'],
                    })
                    created += 1
                except Exception as e:
                    logger.warning(f"Failed to create DEFINITION_OF: {e}")

        logger.info(f"Created {created} DEFINITION_OF edges")
        return created

    def _get_embedding_similarity(self, text1: str, text2: str) -> float:
        if not self.milvus:
            return 0.0
        try:
            import openai
            emb1 = openai.embeddings.create(
                model='text-embedding-3-small',
                input=text1[:500]
            ).data[0].embedding
            emb2 = openai.embeddings.create(
                model='text-embedding-3-small',
                input=text2[:500]
            ).data[0].embedding
            dot = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = sum(a * a for a in emb1) ** 0.5
            norm2 = sum(a * a for a in emb2) ** 0.5
            return dot / (norm1 * norm2) if norm1 and norm2 else 0.0
        except Exception as e:
            logger.warning(f"Embedding similarity failed: {e}")
            return 0.0

    def _check_integrity(self, l1_components: List[Dict], l2_entities: List[Dict]) -> Dict:
        total_l1 = len(l1_components)
        total_l2 = len(l2_entities)

        l1_with_ref = self.neo4j.execute_query('''
            MATCH (c:Component)-[:REFERENCE_OF]->(:L2_Entity)
            WITH count(DISTINCT c) as cnt
            RETURN cnt
        ''')
        l2_with_def = self.neo4j.execute_query('''
            MATCH (e:L2_Entity)-[:DEFINITION_OF]->(:L3_Term)
            WITH count(DISTINCT e) as cnt
            RETURN cnt
        ''')

        l1_covered = l1_with_ref[0]['cnt'] if l1_with_ref else 0
        l2_covered = l2_with_def[0]['cnt'] if l2_with_def else 0

        l1_orphans = self.neo4j.execute_query('''
            MATCH (c:Component)
            WHERE NOT (c)-[:REFERENCE_OF]->(:L2_Entity)
            RETURN c.id as id, c.name as name
            LIMIT 20
        ''')
        l2_orphans = self.neo4j.execute_query('''
            MATCH (e:L2_Entity)
            WHERE NOT (e)-[:DEFINITION_OF]->(:L3_Term)
            RETURN e.id as id, e.name as name
            LIMIT 20
        ''')

        edge_counts = self.neo4j.execute_query('''
            MATCH ()-[r]->()
            WHERE type(r) IN ['REFERENCE_OF', 'DEFINITION_OF', 'CONSTRAINED_BY']
            RETURN type(r) as relation, count(*) as count
        ''')

        return {
            'l1_coverage': f"{l1_covered}/{total_l1} ({100*l1_covered/max(total_l1,1):.1f}%)",
            'l2_coverage': f"{l2_covered}/{total_l2} ({100*l2_covered/max(total_l2,1):.1f}%)",
            'l1_orphan_count': total_l1 - l1_covered,
            'l2_orphan_count': total_l2 - l2_covered,
            'l1_orphans': [{'id': r['id'], 'name': r['name']} for r in (l1_orphans or [])],
            'l2_orphans': [{'id': r['id'], 'name': r['name']} for r in (l2_orphans or [])],
            'edge_counts': {r['relation']: r['count'] for r in (edge_counts or [])},
        }
