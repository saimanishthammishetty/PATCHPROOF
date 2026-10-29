import pytest
from pathlib import Path
from app.services.dependency_parser import DependencyParser
from app.core.config import FIXTURES_DIR

def test_parse_vulnerable_python_fixture():
    fixture_path = FIXTURES_DIR / "vulnerable-python-repo"
    components = DependencyParser.parse_repository(fixture_path)
    
    names = {c.name: c for c in components}
    assert "requests" in names
    assert names["requests"].version == "2.19.1"
    assert names["requests"].ecosystem == "pypi"
    assert names["requests"].purl == "pkg:pypi/requests@2.19.1"
    assert names["requests"].direct is True

    assert "urllib3" in names
    assert names["urllib3"].version == "1.24.1"

    assert "pyyaml" in names
    assert names["pyyaml"].version == "5.2"

def test_parse_vulnerable_node_fixture():
    fixture_path = FIXTURES_DIR / "vulnerable-node-repo"
    components = DependencyParser.parse_repository(fixture_path)
    
    names = {c.name: c for c in components}
    assert "lodash" in names
    assert names["lodash"].version == "4.17.15"
    assert names["lodash"].ecosystem == "npm"
    assert "axios" in names
    assert names["axios"].version == "0.21.1"

def test_parse_secure_go_fixture():
    fixture_path = FIXTURES_DIR / "secure-go-repo"
    components = DependencyParser.parse_repository(fixture_path)
    
    names = {c.name: c for c in components}
    assert "github.com/google/uuid" in names
    assert names["github.com/google/uuid"].version == "1.6.0"
    assert names["github.com/google/uuid"].ecosystem == "golang"
