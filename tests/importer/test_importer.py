import pytest
from src.importer.importer import DataImporter, ImportResult


def test_importer_import():
    assert DataImporter is not None


def test_import_result_success():
    result = ImportResult(True, 'test-id', 'success', 5, 10)
    assert result.success is True
    assert result.doc_id == 'test-id'
    assert result.components == 5
    assert result.terms == 10


def test_import_result_failure():
    result = ImportResult(False, '', 'Error message', 0, 0)
    assert result.success is False
    assert result.message == 'Error message'
