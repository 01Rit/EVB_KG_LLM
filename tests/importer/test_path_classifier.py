import pytest
from src.importer.path_classifier import PathClassifier


def test_path_classifier_import():
    assert PathClassifier is not None


def test_patent_classification():
    classifier = PathClassifier()
    result = classifier.classify('D:/data/专利_动力电池拆卸.pdf')
    assert result['source'] == 'patent'


def test_standard_classification():
    classifier = PathClassifier()
    result = classifier.classify('D:/data/GBT_12345.pdf')
    assert result['source'] == 'standard'


def test_paper_classification():
    classifier = PathClassifier()
    result = classifier.classify('D:/data/学术论文_电池回收.pdf')
    assert result['source'] == 'paper'


def test_other_classification():
    classifier = PathClassifier()
    result = classifier.classify('D:/data/unknown_file.pdf')
    assert result['source'] == 'other'
