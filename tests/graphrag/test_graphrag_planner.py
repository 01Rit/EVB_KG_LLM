import pytest
from src.graphrag.planner import Planner


def test_planner_import():
    assert Planner is not None