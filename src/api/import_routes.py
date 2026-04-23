from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import csv
import io
import uuid
import time
import asyncio

router = APIRouter()

from src.api.progress import SyncProgressTracker


def _auto_score_component(component_name: str, battery_model: str, neo4j_client) -> None:
    """Auto-score a component using three-expert system."""
    try:
        from src.allocator.batch_scorer import BatchScorer
        from src.utils.llm_client import LLMClient
        from src.config import settings

        llm = LLMClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.llm_model
        )
        scorer = BatchScorer(llm, neo4j_client)
        scorer.score_component(component_name, battery_model, '')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Auto-scoring failed for {component_name}: {e}")


class L1ComponentData(BaseModel):
    name: str
    battery_model: str
    tool_required: List[str] = []
    safety_level: int = 1
    precedence: List[str] = []


class ImportStatus(BaseModel):
    total: int
    success: int
    failed: int
    errors: List[str] = []


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post('/import/l1/manual')
async def import_l1_manual(data: L1ComponentData):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    CREATE (c:Component {
        id: $id,
        name: $name,
        battery_model: $battery_model,
        tool_required: $tool_required,
        safety_level: $safety_level,
        precedence: $precedence,
        source_type: 'manual'
    })
    RETURN c
    '''

    try:
        result = neo4j.execute_query(cypher, {
            'id': str(uuid.uuid4()),
            'name': data.name,
            'battery_model': data.battery_model,
            'tool_required': str(data.tool_required),
            'safety_level': data.safety_level,
            'precedence': str(data.precedence)
        })

        if len(result) > 0:
            _auto_score_component(data.name, data.battery_model, neo4j)

        return {'code': 0, 'message': 'Component imported successfully'}
    finally:
        neo4j.close()


@router.post('/import/l1/csv')
async def import_l1_csv(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

    decoded_content = content.decode('utf-8')

    reader = csv.DictReader(io.StringIO(decoded_content))
    rows = list(reader)

    task_id = str(uuid.uuid4())
    total = len(rows) * 2

    SyncProgressTracker._task_info[task_id] = {
        'type': 'l1_csv',
        'total': total,
        'current': 0,
        'stage': 'parsing',
        'message': f'解析CSV文件，共{len(rows)}行',
        'detail': None
    }

    def _do_import():
        import logging
        logger = logging.getLogger(__name__)

        from src.kg.client import Neo4jClient
        from src.config import settings

        neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

        success = 0
        failed = 0
        errors = []

        try:
            for i, row in enumerate(rows):
                try:
                    name = row.get('name', '').strip()
                    battery_model = row.get('battery_model', '').strip()
                    tool_str = row.get('tool_required', '')
                    safety_level = int(row.get('safety_level', 1))
                    precedence_str = row.get('precedence', '')

                    tools = [t.strip() for t in tool_str.split(',') if t.strip()]
                    precedence = [p.strip() for p in precedence_str.split(',') if p.strip()]

                    cypher = '''
                    CREATE (c:Component {
                        id: $id,
                        name: $name,
                        battery_model: $battery_model,
                        tool_required: $tool_required,
                        safety_level: $safety_level,
                        precedence: $precedence,
                        source_type: 'manual'
                    })
                    '''

                    neo4j.execute_query(cypher, {
                        'id': str(uuid.uuid4()),
                        'name': name,
                        'battery_model': battery_model,
                        'tool_required': str(tools),
                        'safety_level': safety_level,
                        'precedence': str(precedence)
                    })

                    SyncProgressTracker.update(
                        task_id, 'creating_nodes',
                        (i + 1) * 2 - 1, total,
                        f'创建组件: {name}',
                        f'进度: {i+1}/{len(rows)}'
                    )

                    try:
                        _auto_score_component(name, battery_model, neo4j)
                    except Exception as score_err:
                        logger.warning(f"[L1 CSV] Scoring failed for {name}: {score_err}")

                    SyncProgressTracker.update(
                        task_id, 'scoring',
                        (i + 1) * 2, total,
                        f'评分组件: {name}',
                        f'进度: {i+1}/{len(rows)}'
                    )

                    success += 1

                except (ValueError, KeyError, RuntimeError) as e:
                    failed += 1
                    errors.append(f'Row {i+1}: {str(e)}')

            SyncProgressTracker.complete(task_id, f'导入完成: 成功{success}个, 失败{failed}个')
            logger.info(f"[L1 CSV] Completed: {success} success, {failed} failed")

        except Exception as e:
            logger.error(f"[L1 CSV] Task {task_id} failed: {e}")
            SyncProgressTracker.error(task_id, str(e))
        finally:
            neo4j.close()

    background_tasks.add_task(_do_import)

    return {
        'code': 0,
        'task_id': task_id,
        'message': f'开始导入{len(rows)}行组件，订阅进度: /api/v1/import/progress/{task_id}',
        'total': len(rows)
    }


@router.post('/import/l1/txt')
async def import_l1_txt(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

    text = content.decode('utf-8')

    task_id = str(uuid.uuid4())

    SyncProgressTracker._task_info[task_id] = {
        'type': 'l1_txt',
        'total': 100,
        'current': 0,
        'stage': 'parsing',
        'message': '解析TXT文件...',
        'detail': None
    }

    def _do_import():
        import logging
        logger = logging.getLogger(__name__)

        from src.importer.entity_extractor import EntityExtractor
        from src.kg.client import Neo4jClient
        from src.utils.llm_client import LLMClient
        from src.config import settings

        neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        llm = LLMClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.llm_model
        )

        try:
            SyncProgressTracker.update(task_id, 'parsing', 5, 100, '使用LLM提取三元组...')
            logger.info(f"[L1 TXT Import] Starting extraction for task {task_id}")

            extractor = EntityExtractor(llm)
            triplets = extractor.extract_triplets(text, filename=file.filename or '')

            logger.info(f"[L1 TXT Import] Extracted {len(triplets)} triplets")

            battery_model = None
            if triplets and 'battery_model' in triplets[0]:
                battery_model = triplets[0]['battery_model']

            SyncProgressTracker.update(task_id, 'parsing', 20, 100, f'提取到{len(triplets)}个三元组')

            nodes_created = 0
            relations_created = 0
            errors = []

            existing_nodes = {}
            for t in triplets:
                if t.get('head'):
                    existing_nodes[t['head']] = battery_model
                if t.get('tail'):
                    existing_nodes[t['tail']] = battery_model

            node_count = len(existing_nodes)
            logger.info(f"[L1 TXT Import] Creating {node_count} nodes")

            for idx, (node_name, node_battery_model) in enumerate(existing_nodes.items()):
                cypher = '''
                MERGE (n:Component {name: $name})
                SET n.source_type = 'l1_txt_import'
                SET n.battery_model = COALESCE($battery_model, 'unknown')
                RETURN n
                '''
                try:
                    neo4j.execute_query(cypher, {'name': node_name, 'battery_model': node_battery_model})
                    nodes_created += 1
                    if node_battery_model and node_battery_model != 'unknown':
                        try:
                            _auto_score_component(node_name, node_battery_model, neo4j)
                        except Exception as score_err:
                            logger.warning(f"[L1 TXT Import] Scoring failed for {node_name}: {score_err}")
                except Exception as e:
                    errors.append(f"Node error: {str(e)}")

                if idx % max(1, node_count // 10) == 0:
                    progress = 20 + int(40 * idx / max(node_count, 1))
                    SyncProgressTracker.update(task_id, 'creating_nodes', progress, 100,
                                              f'创建节点: {node_name}', f'节点进度: {idx+1}/{node_count}')

            SyncProgressTracker.update(task_id, 'creating_nodes', 60, 100, f'节点创建完成: {nodes_created}个')
            logger.info(f"[L1 TXT Import] Created {nodes_created} nodes")

            for idx, t in enumerate(triplets):
                head = t.get('head', '')
                relation = t.get('relation', '')
                tail = t.get('tail', '')
                head_tool = t.get('head_tool', '')
                head_safety = t.get('head_safety', 1)
                tail_tool = t.get('tail_tool', '')
                tail_safety = t.get('tail_safety', 1)

                if not head or not relation or not tail:
                    continue

                cypher = '''
                MATCH (h:Component {name: $head})
                MATCH (t:Component {name: $tail})
                MERGE (h)-[r:RELATES {type: $relation}]->(t)
                SET r.head_tool = $head_tool
                SET r.head_safety = $head_safety
                SET r.tail_tool = $tail_tool
                SET r.tail_safety = $tail_safety
                RETURN h, r, t
                '''
                try:
                    neo4j.execute_query(cypher, {
                        'head': head,
                        'relation': relation,
                        'tail': tail,
                        'head_tool': head_tool,
                        'head_safety': head_safety,
                        'tail_tool': tail_tool,
                        'tail_safety': tail_safety
                    })
                    relations_created += 1
                except Exception as e:
                    errors.append(f"Relation error: {str(e)}")

                if idx % max(1, len(triplets) // 10) == 0:
                    progress = 60 + int(35 * idx / max(len(triplets), 1))
                    SyncProgressTracker.update(task_id, 'creating_relations', progress, 100,
                                              f'创建关系: {relation}', f'关系进度: {idx+1}/{len(triplets)}')

            logger.info(f"[L1 TXT Import] Completed: {nodes_created} nodes, {relations_created} relations")
            SyncProgressTracker.complete(task_id, f'导入完成: {nodes_created}节点, {relations_created}关系')

        except Exception as e:
            logger.error(f"[L1 TXT Import] Failed task {task_id}: {e}")
            SyncProgressTracker.error(task_id, str(e))
        finally:
            neo4j.close()

    background_tasks.add_task(_do_import)

    return {
        'code': 0,
        'task_id': task_id,
        'message': f'开始导入TXT三元组，订阅进度: /api/v1/import/progress/{task_id}'
    }


def _extract_pdf_text(content: bytes) -> str:
    import fitz
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        full_text = ''
        for page in doc:
            full_text += page.get_text()
        doc.close()

        if _is_garbled_text(full_text):
            import pdfplumber
            with pdfplumber.open(tmp_path) as pdf:
                full_text = ''
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + '\n\n'

        if _is_garbled_text(full_text):
            full_text = _extract_with_pymupdf_dict(tmp_path)

        if _is_garbled_text(full_text):
            full_text = _extract_fallback_methods(tmp_path)

        return full_text
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _extract_with_pymupdf_dict(tmp_path: str) -> str:
    import fitz
    doc = fitz.open(tmp_path)
    full_text = ''
    for page in doc:
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        full_text += span.get("text", "")
                    full_text += "\n"
    doc.close()
    return full_text


def _extract_fallback_methods(tmp_path: str) -> str:
    import fitz
    import logging
    logger = logging.getLogger(__name__)

    methods = [
        ("blocks", lambda p: "\n".join(
            span.get("text", "") for block in p.get_text("dict", flags=0).get("blocks", []) if block.get("type") == 0
            for line in block.get("lines", []) for span in line.get("spans", [])
        )),
        ("xhtml", lambda p: p.get_text("xhtml")),
        ("xml", lambda p: p.get_text("xml")),
    ]

    for method_name, extract_func in methods:
        try:
            doc = fitz.open(tmp_path)
            text = ""
            for page in doc:
                text += extract_func(page) + "\n"
            doc.close()
            if text.strip() and not _is_garbled_text(text):
                logger.info(f"PymuPDF {method_name} extraction succeeded")
                return text
        except Exception as e:
            logger.warning(f"PymuPDF {method_name} extraction failed: {e}")

    return ""


def _is_garbled_text(text: str) -> bool:
    if not text or len(text.strip()) < 50:
        return True
    chinese_chars = [c for c in text if 0x4E00 <= ord(c) <= 0x9FFF]
    compat_chars = [c for c in text if 0xF900 <= ord(c) <= 0xFAFF]
    if len(chinese_chars) > 0 and len(compat_chars) > 0:
        ratio = len(compat_chars) / max(len(chinese_chars), 1)
        if ratio > 0.3:
            return True
    if '犐犆犛' in text or '犐犆犇' in text:
        return True
    return False


@router.post('/import/l1/pdf')
async def import_l1_pdf(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

    text = _extract_pdf_text(content)

    if not text.strip():
        raise HTTPException(status_code=400, detail='PDF is empty or could not extract text')

    from src.importer.entity_extractor import EntityExtractor
    from src.utils.llm_client import LLMClient
    from src.config import settings

    llm = LLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_model
    )
    extractor = EntityExtractor(llm)

    triplets = extractor.extract_triplets(text)

    from src.kg.client import Neo4jClient

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    try:
        nodes_created = 0
        relations_created = 0
        errors = []

        existing_nodes = set()
        for t in triplets:
            if t.get('head'):
                existing_nodes.add(t['head'])
            if t.get('tail'):
                existing_nodes.add(t['tail'])

        for node_name in existing_nodes:
            cypher = '''
            MERGE (n:Entity {name: $name})
            SET n.source_type = 'l1_import'
            RETURN n
            '''
            try:
                neo4j.execute_query(cypher, {'name': node_name})
                nodes_created += 1
            except Exception as e:
                errors.append(f"Node error: {str(e)}")

        for t in triplets:
            head = t.get('head', '')
            relation = t.get('relation', '')
            tail = t.get('tail', '')

            if not head or not relation or not tail:
                continue

            cypher = '''
            MATCH (h:Entity {name: $head})
            MATCH (t:Entity {name: $tail})
            MERGE (h)-[r:RELATES {type: $relation}]->(t)
            RETURN h, r, t
            '''
            try:
                neo4j.execute_query(cypher, {
                    'head': head,
                    'relation': relation,
                    'tail': tail
                })
                relations_created += 1
            except Exception as e:
                errors.append(f"Relation error: {str(e)}")

        return {
            'code': 0,
            'message': f'Imported {nodes_created} entities, {relations_created} relations',
            'nodes': nodes_created,
            'relations': relations_created,
            'errors': errors[:10]
        }
    finally:
        neo4j.close()


@router.post('/import/l2')
async def import_l2(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

    full_text = _extract_pdf_text(content)

    if not full_text.strip():
        raise HTTPException(status_code=400, detail='PDF is empty or could not extract text')

    from src.config import settings

    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail='OpenAI API key not configured')

    task_id = str(uuid.uuid4())

    SyncProgressTracker._task_info[task_id] = {
        'type': 'l2',
        'total': 100,
        'current': 0,
        'stage': 'parsing',
        'message': '准备解析PDF...',
        'detail': None
    }

    def _do_import():
        from src.importer.l2_importer import L2Importer
        from src.kg.client import Neo4jClient
        from src.utils.llm_client import LLMClient
        from src.config import settings

        neo4j = None
        try:
            neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            llm = LLMClient(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.llm_model
            )

            def progress_callback(stage: str, current: int, total: int, message: str, detail: str = None):
                SyncProgressTracker.update(task_id, stage, current, total, message, detail)

            importer = L2Importer(neo4j, llm, progress_callback=progress_callback)
            result = importer.import_pdf(full_text, file.filename or 'unknown')

            SyncProgressTracker.complete(task_id, f'L2导入完成: {result["entities_created"]}实体, {result["terms_created"]}术语, {result["relations_created"]}关系')

        except Exception as e:
            logger.error(f"L2 import failed: {e}")
            SyncProgressTracker.error(task_id, str(e))
        finally:
            if neo4j:
                neo4j.close()

    background_tasks.add_task(_do_import)

    return {
        'code': 0,
        'task_id': task_id,
        'message': f'开始L2导入，订阅进度: /api/v1/import/progress/{task_id}'
    }


@router.post('/import/l3')
async def import_l3(data: Dict[str, Any]):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    terms = data.get('terms', [])

    try:
        for term in terms:
            cypher = '''
            CREATE (t:Term {
                term_id: $term_id,
                definition: $definition,
                units: $units,
                source_type: 'manual'
            })
            '''

            neo4j.execute_query(cypher, {
                'term_id': term.get('term_id', ''),
                'definition': term.get('definition', ''),
                'units': term.get('units', '')
            })

        return {'code': 0, 'message': f'Imported {len(terms)} terms'}
    finally:
        neo4j.close()


@router.get('/import/status')
async def get_import_status():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher_components = 'MATCH (c:Component) RETURN count(c) as count'
    cypher_documents = 'MATCH (d:Document) RETURN count(d) as count'
    cypher_terms = 'MATCH (t:Term) RETURN count(t) as count'

    try:
        comp_count = neo4j.execute_query(cypher_components)[0].get('count', 0)
        doc_count = neo4j.execute_query(cypher_documents)[0].get('count', 0)
        term_count = neo4j.execute_query(cypher_terms)[0].get('count', 0)

        return {
            'components': comp_count,
            'documents': doc_count,
            'terms': term_count
        }
    finally:
        neo4j.close()
