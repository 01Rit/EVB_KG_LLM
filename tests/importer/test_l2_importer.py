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
    assert call_args[0][0] == '''CREATE (d:L2_Document {doc_id: $doc_id, name: $name, source: $source, content: $content, node_type: 'L2_Document'})'''


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


def test_create_l3_terms():
    mock_neo4j = Mock()
    mock_neo4j.execute_query.return_value = [{'cnt': 1}]
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    terms = [{'term_id': 'T1', 'name': '预紧力', 'definition': 'definition text'}]

    count = importer._create_l3_terms('test-doc-id', terms)

    assert count == 1
    mock_neo4j.execute_query.assert_called_once()


def test_create_cross_layer_relations():
    mock_neo4j = Mock()
    mock_neo4j.execute_query.return_value = [{'cnt': 1}]
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    entities = [
        {'name': '预紧力定义', 'entity_type': 'definition', 'source_evidence': '', 'battery_model': ''},
        {'name': '电池包', 'entity_type': 'component', 'source_evidence': '', 'battery_model': ''},
        {'name': '扭矩扳手', 'entity_type': 'tool', 'source_evidence': '', 'battery_model': ''}
    ]
    terms = [{'term_id': 'T1', 'name': '预紧力', 'definition': '预紧力定义'}]

    relations = importer._create_cross_layer_relations('test-doc-id', entities, terms)

    assert relations > 0
