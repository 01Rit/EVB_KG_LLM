import pytest


def test_routes_import():
    from src.api import routes
    assert routes.router is not None