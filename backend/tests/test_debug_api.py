import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_debug_analyze_valid_mutable_default():
    payload = {
        "code": "def process_batch(item, queue=[]):\n    queue.append(item)\n    return queue\n",
        "language": "python"
    }
    response = client.post("/api/debug/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["issue_detected"] is True
    assert data["predicted_category"] in ("api_misuse", "type_error")
    assert data["confidence_score"] > 0.0
    assert data["faulty_line_number"] == 1
    assert "queue=[]" in data["faulty_line_content"]
    assert data["suggested_fix"] is not None
    assert "queue=None" in data["suggested_fix"]
    assert data["diff"] is not None
    assert "--- original" in data["diff"]

def test_debug_analyze_clean_code():
    payload = {
        "code": "def filter_positives(items):\n    return [x for x in items if x > 0]\n",
        "language": "python"
    }
    response = client.post("/api/debug/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["predicted_category"] == "none_correct_code"
    assert data["issue_detected"] is False
    assert data["severity"] == "INFO"
    assert data["faulty_line_number"] is None

def test_debug_analyze_empty_code():
    response = client.post("/api/debug/analyze", json={"code": "   ", "language": "python"})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]

def test_debug_analyze_oversized_code():
    huge_code = "x = 1\n" * 25000  # > 120,000 chars
    response = client.post("/api/debug/analyze", json={"code": huge_code, "language": "python"})
    assert response.status_code == 400
    assert "exceeds maximum allowed size" in response.json()["detail"]

def test_debug_analyze_unsupported_language():
    response = client.post("/api/debug/analyze", json={"code": "puts 'hello'", "language": "ruby"})
    assert response.status_code == 400
    assert "is not supported" in response.json()["detail"]

def test_debug_analyze_javascript_loose_equality():
    payload = {
        "code": "function checkStatus(val) {\n    if (val == 0) {\n        return 'ZERO';\n    }\n    return 'OTHER';\n}\n",
        "language": "javascript"
    }
    response = client.post("/api/debug/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["predicted_category"] == "condition_error"
    assert data["faulty_line_number"] == 2
    assert "===" in data["suggested_fix"]

def test_debug_analyze_response_schema_compatibility():
    """
    Regression test for ISS-02:
    CodeDebugResponse must provide both canonical fields (predicted_category,
    confidence_score, suggested_fix) and backward-compatible integration fields
    (detected_archetype, confidence, proposed_fixes) with synchronized values.
    """
    # 1. Defective snippet
    payload = {
        "code": "def process_data(items=[]):\n    items.append(1)\n    return items\n",
        "language": "python"
    }
    resp = client.post("/api/debug/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Verify canonical and alias archetype/category
    assert data["issue_detected"] is True
    assert data["predicted_category"] == "api_misuse"
    assert data["detected_archetype"] == "api_misuse"

    # Verify confidence fields are numeric floats between 0 and 1
    assert isinstance(data["confidence_score"], float)
    assert isinstance(data["confidence"], float)
    assert data["confidence"] == data["confidence_score"]
    assert 0.0 <= data["confidence"] <= 1.0

    # Verify proposed fixes list contains the suggested fix
    assert isinstance(data["proposed_fixes"], list)
    assert len(data["proposed_fixes"]) >= 1
    assert data["suggested_fix"] in data["proposed_fixes"]

    # 2. Clean code snippet
    clean_resp = client.post("/api/debug/analyze", json={
        "code": "def add(a, b):\n    return a + b\n",
        "language": "python"
    })
    assert clean_resp.status_code == 200
    clean_data = clean_resp.json()
    assert clean_data["issue_detected"] is False
    assert clean_data["predicted_category"] == "none_correct_code"
    assert clean_data["detected_archetype"] == "none_correct_code"
    assert clean_data["confidence"] == clean_data["confidence_score"]
    assert clean_data["suggested_fix"] is None
    assert clean_data["proposed_fixes"] == []
