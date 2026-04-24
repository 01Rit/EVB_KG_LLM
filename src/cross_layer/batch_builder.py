import re
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Layer 1: 手工词典 (English -> [Chinese aliases])
MANUAL_ALIAS_DICT = {
    "battery module": ["电池模块", "电池模组", "模块"],
    "busbar": ["汇流排", "母线"],
    "electrolyte": ["电解液"],
    "cell": ["电芯"],
    "tab": ["极耳"],
    "connector": ["连接器", "接插件"],
    "housing": ["外壳", "壳体"],
    "insulator": ["绝缘体", "绝缘板"],
    "cooling plate": ["冷却板"],
    "thermal pad": ["导热垫"],
    "bms": ["电池管理系统"],
    "fuse": ["熔断器", "保险丝"],
    "battery pack": ["电池包"],
    "module": ["模块", "模组"],
    "cover": ["盖", "盖板"],
    "plate": ["板", "板材"],
    "pack": ["包", "电池包"],
    "case": ["壳体", "外壳"],
    "housing": ["壳体", "外壳"],
    "seal": ["密封件"],
    "gasket": ["密封垫"],
    "terminal": ["端子", "极柱"],
    "cable": ["电缆", "线束"],
    "wire": ["导线", "电线"],
    "sensor": ["传感器"],
    "pcb": ["印刷电路板"],
    "battery management system": ["电池管理系统"],
    "thermal management": ["热管理"],
    "cooling": ["冷却"],
    "heating": ["加热"],
    "vent": ["通风口"],
    "valve": ["阀门"],
    "filter": ["过滤器"],
    "pump": ["泵"],
    "pipe": ["管", "管道"],
    "hose": ["软管"],
    "clamp": ["卡箍"],
    "bracket": ["支架"],
    "bolt": ["螺栓", "螺丝"],
    "screw": ["螺丝", "螺钉"],
    "nut": ["螺母"],
    "washer": ["垫圈"],
    "sealant": ["密封胶"],
    "adhesive": ["粘合剂"],
    "label": ["标签"],
    "manual": ["手册"],
    "instruction": ["说明书"],
    "battery": ["电池"],
    "power": ["电源", "电力"],
    "energy": ["能量"],
    "voltage": ["电压"],
    "current": ["电流"],
    "temperature": ["温度"],
    "pressure": ["压力"],
    "humidity": ["湿度"],
    "safety": ["安全"],
    "warning": ["警告"],
    "caution": ["注意"],
    "danger": ["危险"],
    "note": ["注意", "说明"],
}

# Stopwords 过滤列表
STOPWORDS = {"system", "device", "component", "unit", "part", "item", "element", "module"}

# 自动抽取正则模式
EXTRACTION_PATTERNS = [
    r'([\u4e00-\u9fa5]+)[（(]([A-Za-z0-9\s\-]+)[）)]',  # Pattern A: 中文→英文
    r'([A-Za-z0-9\s\-]+)[（(]([\u4e00-\u9fa5]+)[）)]',  # Pattern B: 英文→中文
    r'([\u4e00-\u9fa5]+)\s*\[([A-Za-z0-9\s\-]+)\]',      # Pattern C: 方括号
    r'([\u4e00-\u9fa5]+)\s*-\s*([A-Za-z0-9\s\-]+)',       # Pattern D: 破折号
]

# 关键词检测 (用于 DEFINITION_OF)
DEFINITION_KEYWORDS = ['is a', 'refers to', 'defined as', 'definition of', 'means', 'is defined', 'represent', 'denote']


def normalize_term(name: str) -> str:
    """规范化术语：去连字符/复数/单位/括号内容"""
    if not name:
        return ''
    n = name.lower().strip()
    # 去括号内容
    n = re.sub(r'\s*\([^)]*\)', '', n)
    n = re.sub(r'\s*\[[^\]]*\]', '', n)
    # 去连字符
    n = re.sub(r'[-\s_]+', ' ', n)
    # 去复数（简单规则）
    if n.endswith('s') and len(n) > 2:
        n = n[:-1]
    # 去单位/编号（M6, #12等）
    n = re.sub(r'\b[M#]?\d+\b', '', n)
    n = n.strip()
    return n


def is_valid_term(term: str, is_english: bool) -> bool:
    """验证术语是否有效"""
    term = term.strip()
    if not term or len(term) < 2:
        return False
    term_lower = term.lower()
    if term_lower in STOPWORDS:
        return False
    if is_english:
        tokens = term.split()
        if len(tokens) > 4:
            return False
    else:
        if len(term) > 10:
            return False
    # 过滤含"应/可/用于"等非术语
    noise_words = ['应', '可', '用于', '必须', '应该', '需要', '采用', '通过']
    if any(w in term for w in noise_words):
        return False
    return True


def extract_alias_pairs(text: str) -> List[Tuple[str, str]]:
    """从文本中抽取中英文术语对"""
    pairs = []
    for pattern in EXTRACTION_PATTERNS:
        matches = re.findall(pattern, text, re.UNICODE)
        for match in matches:
            if len(match) == 2:
                # 判断哪个是英文哪个是中文
                if re.search(r'[\u4e00-\u9fa5]', match[0]):
                    chinese, english = match[0], match[1]
                else:
                    english, chinese = match[0], match[1]
                english = english.strip().lower()
                chinese = chinese.strip()
                english_norm = normalize_term(english)
                chinese_norm = normalize_term(chinese)
                if english_norm and chinese_norm and is_valid_term(english_norm, True) and is_valid_term(chinese_norm, False):
                    pairs.append((english_norm, chinese_norm))
    return pairs


def build_extended_alias_dict() -> Dict[str, List[str]]:
    """构建扩展 alias dictionary (English -> [Chinese aliases])"""
    # Layer 1: 手工词典 (已定义)
    merged = dict(MANUAL_ALIAS_DICT)
    return merged


def build_alias_sets(alias_dict: Dict[str, List[str]] = None) -> Dict[str, Set[str]]:
    """从 alias_dict 构建 alias_sets"""
    if alias_dict is None:
        alias_dict = build_extended_alias_dict()
    alias_map: Dict[str, Set[str]] = {}
    for english, chinese_list in alias_dict.items():
        norm_en = normalize_term(english)
        if norm_en not in alias_map:
            alias_map[norm_en] = set()
        for chinese in chinese_list:
            norm_cn = normalize_term(chinese)
            if is_valid_term(norm_cn, False):
                alias_map[norm_en].add(norm_cn)
                # 双向添加
                if norm_cn not in alias_map:
                    alias_map[norm_cn] = set()
                alias_map[norm_cn].add(norm_en)
    return alias_map


def deduplicate_aliases(aliases: List[str]) -> List[str]:
    """优先保留更长、更具体的中文"""
    aliases = list(set(aliases))
    aliases.sort(key=len, reverse=True)
    return aliases


def are_aliases(name1: str, name2: str, alias_sets: Dict[str, Set[str]]) -> Tuple[bool, float]:
    """判断两个名称是否为 alias，返回 (is_alias, score)"""
    n1 = normalize_term(name1)
    n2 = normalize_term(name2)

    # 1. 精确匹配
    if n1 == n2:
        return True, 1.0

    # 2. alias set 匹配
    if n1 in alias_sets and n2 in alias_sets[n1]:
        return True, 1.0
    if n2 in alias_sets and n1 in alias_sets[n2]:
        return True, 1.0

    # 3. contains 匹配
    if n1 in n2 or n2 in n1:
        return True, 0.8

    return False, 0.0


def names_match(name1: str, name2: str) -> bool:
    n1 = normalize_term(name1)
    n2 = normalize_term(name2)
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
    text_lower = text.lower()
    return any(kw in text_lower for kw in DEFINITION_KEYWORDS)


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
        self.alias_dict = build_extended_alias_dict()
        self.alias_sets = build_alias_sets(self.alias_dict)
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
                is_alias, alias_score = are_aliases(l1['name'], l2['name'], self.alias_sets)
                if is_alias:
                    source = 'alias' if alias_score >= 1.0 else 'contains'
                    confidence = alias_score
                elif names_match(l1['name'], l2['name']):
                    is_alias = True
                    source = 'name_match'
                    confidence = 0.8
                else:
                    is_alias = False

                if is_alias:
                    matches.append({
                        'source_name': l1['name'],
                        'target_id': l2['id'],
                        'confidence': confidence,
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
                is_alias, alias_score = are_aliases(l2['name'], l3['name'], self.alias_sets)

                if is_alias:
                    source = 'alias'
                    confidence = alias_score
                elif names_match(l2['name'], l3['name']):
                    is_alias = True
                    source = 'name_match'
                    confidence = 0.85
                elif definition_keywords_in_text(l2.get('source_evidence', '')) and names_match(l2['name'], l3['name']):
                    is_alias = True
                    source = 'keyword_detection'
                    confidence = 0.80
                else:
                    is_alias = False
                    confidence = 0.0

                if not is_alias and self.milvus:
                    try:
                        sim = self._get_embedding_similarity(l2['name'], l3['name'])
                        if sim > SIMILARITY_THRESHOLD:
                            is_alias = True
                            source = 'embedding'
                            confidence = sim
                    except Exception:
                        pass

                if is_alias and confidence > 0:
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
            RETURN c.name as name
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
            'l1_orphans': [r.get('name', '') for r in (l1_orphans or [])],
            'l2_orphans': [{'id': r.get('id', ''), 'name': r.get('name', '')} for r in (l2_orphans or [])],
            'edge_counts': {r['relation']: r['count'] for r in (edge_counts or [])},
        }
