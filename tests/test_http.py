import pytest
from pathlib import Path

from krules_companion_client.http import HttpClient


@pytest.fixture
def configfile_path():
    return Path(__file__).resolve().parent / 'testconfig'


def test_http_client_readconfigs(configfile_path):

    HttpClient(config=configfile_path)

    from krules_companion_client.commands import defaults
    assert defaults.get("address") == "http://example.com"