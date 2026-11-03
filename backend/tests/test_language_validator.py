import pytest
from scripts.datasets.schema import CodeDebuggingExample

def test_language_normalization_cpp_and_cplusplus():
    ex_cpp = CodeDebuggingExample(
        language="cpp",
        bug_category="test",
        original_code="int main(){return 0;}",
        bug_description="none",
        source_dataset="test",
        source_record_id="l-1",
    )
    assert ex_cpp.language == "cpp"

    ex_cxx = CodeDebuggingExample(
        language="c++",
        bug_category="test",
        original_code="int main(){return 0;}",
        bug_description="none",
        source_dataset="test",
        source_record_id="l-2",
    )
    assert ex_cxx.language == "cpp"
