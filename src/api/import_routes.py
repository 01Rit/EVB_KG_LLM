from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import csv
import io
import uuid

router = APIRouter()


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

        return {'code': 0, 'message': 'Component imported successfully'}
    finally:
        neo4j.close()


@router.post('/import/l1/csv')
async def import_l1_csv(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

    decoded_content = content.decode('utf-8')

    reader = csv.DictReader(io.StringIO(decoded_content))
    rows = list(reader)

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

                success += 1

            except (ValueError, KeyError, RuntimeError) as e:
                failed += 1
                errors.append(f'Row {i+1}: {str(e)}')

        return {
            'code': 0,
            'message': f'Import completed',
            'total': len(rows),
            'success': success,
            'failed': failed,
            'errors': errors
        }
    finally:
        neo4j.close()


@router.post('/import/l1/txt')
async def import_l1_txt(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

    text = content.decode('utf-8')

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
        extractor = EntityExtractor(llm)
        triplets = extractor.extract_triplets(text, filename=file.filename or '')

        battery_model = None
        if triplets and 'battery_model' in triplets[0]:
            battery_model = triplets[0]['battery_model']

        nodes_created = 0
        relations_created = 0
        errors = []

        existing_nodes = {}
        for t in triplets:
            if t.get('head'):
                existing_nodes[t['head']] = battery_model
            if t.get('tail'):
                existing_nodes[t['tail']] = battery_model

        for node_name, node_battery_model in existing_nodes.items():
            cypher = '''
            MERGE (n:Component {name: $name})
            SET n.source_type = 'l1_txt_import'
            SET n.battery_model = COALESCE($battery_model, 'unknown')
            RETURN n
            '''
            try:
                neo4j.execute_query(cypher, {'name': node_name, 'battery_model': node_battery_model})
                nodes_created += 1
            except Exception as e:
                errors.append(f"Node error: {str(e)}")

        for t in triplets:
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

        return {
            'code': 0,
            'message': f'Imported {nodes_created} entities, {relations_created} relations',
            'nodes': nodes_created,
            'relations': relations_created,
            'errors': errors[:10]
        }
    finally:
        neo4j.close()


@router.post('/import/l1/pdf')
async def import_l1_pdf(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

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
    finally:
        os.unlink(tmp_path)

    from src.importer.entity_extractor import EntityExtractor
    from src.utils.llm_client import LLMClient
    from src.config import settings

    llm = LLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_model
    )
    extractor = EntityExtractor(llm)

    triplets = extractor.extract_triplets(full_text)

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
async def import_l2(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

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
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not full_text.strip():
        raise HTTPException(status_code=400, detail='PDF is empty or could not extract text')

    from src.importer.entity_extractor import EntityExtractor
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings

    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail='OpenAI API key not configured')

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_model
    )

    try:
        extractor = EntityExtractor(llm)
        
        try:
            triplets = extractor.extract_triplets(full_text, filename=file.filename or '')
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise HTTPException(status_code=500, detail=f'LLM extraction failed: {str(e)}')

        doc_cypher = '''
        CREATE (d:Document {
            doc_id: $doc_id,
            title: $title,
            content: $content,
            source_type: 'l2_import'
        })
        RETURN d
        '''
        doc_id = str(uuid.uuid4())
        neo4j.execute_query(doc_cypher, {
            'doc_id': doc_id,
            'title': file.filename or 'unknown',
            'content': full_text[:50000]
        })

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
            SET n.doc_id = $doc_id
            RETURN n
            '''
            try:
                neo4j.execute_query(cypher, {'name': node_name, 'doc_id': doc_id})
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
            MERGE (h)-[r:RELATES {type: $relation, doc_id: $doc_id}]->(t)
            RETURN h, r, t
            '''
            try:
                neo4j.execute_query(cypher, {
                    'head': head,
                    'relation': relation,
                    'tail': tail,
                    'doc_id': doc_id
                })
                relations_created += 1
            except Exception as e:
                errors.append(f"Relation error: {str(e)}")

        return {
            'code': 0,
            'message': f'Document imported with {nodes_created} entities, {relations_created} relations',
            'doc_id': doc_id,
            'nodes': nodes_created,
            'relations': relations_created,
            'errors': errors[:10]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"L2 import failed: {e}")
        raise HTTPException(status_code=500, detail=f'L2 import failed: {str(e)}')
    finally:
        neo4j.close()


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
