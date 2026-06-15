import pytest

FIXTURES = None


def pytest_configure(config):
    config.addinivalue_line("markers", "live: hits real network endpoints")
