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

    components = []
    current = {}

    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('[组件'):
            if current:
                components.append(current)
            current = {}
        elif ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            current[key] = value

    if current:
        components.append(current)

    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    success = 0
    errors = []

    try:
        for comp in components:
            try:
                name = comp.get('名称', comp.get('name', ''))
                battery_model = comp.get('型号', comp.get('battery_model', ''))
                tools_str = comp.get('工具', comp.get('tool_required', ''))
                safety_level = int(comp.get('安全等级', comp.get('safety_level', 1)))
                precedence_str = comp.get('依赖', comp.get('precedence', ''))

                tools = [t.strip() for t in tools_str.split(',') if t.strip()]
                precedence = [p.strip() for p in precedence_str.split(';') if p.strip()]

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
                errors.append(f'Component {name}: {str(e)}')

        return {'code': 0, 'message': f'Imported {success} components', 'errors': errors}
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

    llm = LLMClient(settings.openai_api_key, settings.openai_base_url)
    extractor = EntityExtractor(llm)

    components = extractor.extract_components(full_text)

    from src.kg.client import Neo4jClient

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    try:
        for comp in components:
            cypher = '''
            CREATE (c:Component {
                id: $id,
                name: $name,
                battery_model: $battery_model,
                tool_required: $tool_required,
                safety_level: $safety_level,
                precedence: $precedence,
                source_type: 'pdf_import'
            })
            '''

            neo4j.execute_query(cypher, {
                'id': str(uuid.uuid4()),
                'name': comp.get('name', ''),
                'battery_model': comp.get('category', ''),
                'tool_required': str(comp.get('tools', [])),
                'safety_level': comp.get('safety_level', 1),
                'precedence': str(comp.get('dependencies', []))
            })

        return {'code': 0, 'message': f'Extracted {len(components)} components from PDF'}
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
        os.unlink(tmp_path)

    from src.importer.importer import DataImporter
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(settings.openai_api_key, settings.openai_base_url)

    try:
        importer = DataImporter(neo4j, llm)

        result = importer.import_pdf(tmp_path)

        return {
            'code': 0,
            'message': f'Document imported',
            'doc_id': result.doc_id,
            'components': result.components,
            'terms': result.terms
        }
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
