import pytest


def test_routes_import():
    from src.api import routes
    assert routes.router is not None


def test_import_l2_schema_validation():
    from src.api.schemas import L2EntityData, L2DocumentData, L3TermData
    entity = L2EntityData(name='电池包', entity_type='component', source_evidence='原文')
    assert entity.name == '电池包'
    assert entity.entity_type == 'component'

    term = L3TermData(term_id='T1', name='预紧力', definition='定义')
    assert term.name == '预紧力'