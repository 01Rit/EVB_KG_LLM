import pytest
from src.importer.pdf_parser import PDFParser


def test_pdf_parser_import():
    assert PDFParser is not None


def test_pdf_parser_initialization():
    parser = PDFParser()
    assert parser.extract_images is False


def test_pdf_parser_with_images():
    parser = PDFParser(extract_images=True)
    assert parser.extract_images is True