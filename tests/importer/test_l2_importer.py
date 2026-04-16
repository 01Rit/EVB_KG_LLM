import pytest
from unittest.mock import Mock, MagicMock
from src.importer.l2_importer import L2Importer


def test_l2_importer_init():
    mock_neo4j = Mock()
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)
    assert importer.neo4j is mock_neo4j
    assert importer.extractor is not None


def test_create_l2_document():
    mock_neo4j = Mock()
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    importer._create_l2_document('test-doc-id', 'test.pdf', 'full text')

    mock_neo4j.execute_query.assert_called_once()
    call_args = mock_neo4j.execute_query.call_args
    cypher = call_args[0][0]
    params = call_args[1]

    assert cypher == '''CREATE (d:L2_Document {doc_id: $doc_id, name: $name, source: $source, content: $content, node_type: 'L2_Document'})'''
    assert params['doc_id'] == 'test-doc-id'
    assert params['name'] == 'test.pdf'
    assert params['source'] == 'test.pdf'
    assert params['content'] == 'full text'


def test_create_l2_entities():
    mock_neo4j = Mock()
    mock_neo4j.execute_query.return_value = [{'cnt': 2}]
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    entities = [
        {'name': '电池包', 'entity_type': 'component', 'source_evidence': '原文', 'battery_model': 'test'},
        {'name': '扭矩扳手', 'entity_type': 'tool', 'source_evidence': '原文', 'battery_model': 'test'}
    ]

    count = importer._create_l2_entities('test-doc-id', entities)

    assert count == 2
    mock_neo4j.execute_query.assert_called_once()
    call_args = mock_neo4j.execute_query.call_args
    params = call_args[1]

    assert 'entities' in params
    entity_data = params['entities']
    assert len(entity_data) == 2

    assert entity_data[0]['name'] == '电池包'
    assert entity_data[0]['entity_type'] == 'component'
    assert entity_data[0]['source_evidence'] == '原文'
    assert entity_data[0]['battery_model'] == 'test'
    assert 'id' in entity_data[0]

    assert entity_data[1]['name'] == '扭矩扳手'
    assert entity_data[1]['entity_type'] == 'tool'
    assert entity_data[1]['source_evidence'] == '原文'
    assert entity_data[1]['battery_model'] == 'test'
    assert 'id' in entity_data[1]


def test_create_l2_entities_empty():
    mock_neo4j = Mock()
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    count = importer._create_l2_entities('test-doc-id', [])

    assert count == 0
    mock_neo4j.execute_query.assert_not_called()


def test_create_l3_terms():
    mock_neo4j = Mock()
    mock_neo4j.execute_query.return_value = [{'cnt': 1}]
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    terms = [{'term_id': 'T1', 'name': '预紧力', 'definition': 'definition text'}]

    count = importer._create_l3_terms('test-doc-id', terms)

    assert count == 1
    mock_neo4j.execute_query.assert_called_once()
    call_args = mock_neo4j.execute_query.call_args
    params = call_args[1]

    assert 'terms' in params
    term_data = params['terms']
    assert len(term_data) == 1
    assert term_data[0]['term_id'] == 'T1'
    assert term_data[0]['name'] == '预紧力'
    assert term_data[0]['definition'] == 'definition text'
    assert 'id' in term_data[0]


def test_create_cross_layer_relations():
    mock_neo4j = Mock()
    mock_neo4j.execute_query.side_effect = [
        [{'cnt': 1}],  # DEFINED_AS
        [{'cnt': 0}],  # USES_TOOL (no component+tool pair matches criteria)
        [{'cnt': 3}],  # ORIGINATED_FROM (3 terms)
        [{'cnt': 3}],  # REFERENCED_IN (3 entities)
    ]
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    entities = [
        {'name': '预紧力定义', 'entity_type': 'definition', 'source_evidence': '', 'battery_model': ''},
        {'name': '电池包', 'entity_type': 'component', 'source_evidence': '', 'battery_model': ''},
        {'name': '扭矩扳手', 'entity_type': 'tool', 'source_evidence': '', 'battery_model': ''}
    ]
    terms = [
        {'term_id': 'T1', 'name': '预紧力', 'definition': '预紧力定义'},
        {'term_id': 'T2', 'name': '扭矩', 'definition': '扭矩定义'},
        {'term_id': 'T3', 'name': '力矩', 'definition': '力矩定义'},
    ]

    relations = importer._create_cross_layer_relations('test-doc-id', entities, terms)

    assert relations == 7  # 1 DEFINED_AS + 0 USES_TOOL + 3 ORIGINATED_FROM + 3 REFERENCED_IN

    calls = mock_neo4j.execute_query.call_args_list
    assert len(calls) == 4

    defined_as_cypher = calls[0][0][0]
    assert 'DEFINED_AS' in defined_as_cypher

    uses_tool_cypher = calls[1][0][0]
    assert 'USES_TOOL' in uses_tool_cypher

    originated_from_cypher = calls[2][0][0]
    assert 'ORIGINATED_FROM' in originated_from_cypher

    referenced_in_cypher = calls[3][0][0]
    assert 'REFERENCED_IN' in referenced_in_cypher