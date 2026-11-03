"""
Dual-Channel Feature Extraction Pipeline for Experiment H.
Channel A: AST Structural Representation (normalized identifiers, structural control flow).
Channel B: Lexical & Semantic Representation (subwords, type suffixes, API calls, original tokens).
"""

import re
from typing import Tuple, List

# Regex patterns for subword and suffix extraction
CAMEL_CASE_REGEX = re.compile(r'([a-z0-9])([A-Z])')
IDENTIFIER_REGEX = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')

KNOWN_TYPE_SUFFIXES = [
    '_str', '_string', '_num', '_number', '_int', '_integer',
    '_id', '_float', '_list', '_dict', '_map', '_bool', '_ptr',
    '_len', '_size', '_buf', '_buffer', '_arr', '_array', '_cnt', '_count'
]

def extract_channel_b_lexical(code: str, language: str = "") -> str:
    """
    Extracts lexical and semantic features from original code:
    1. Preserves original code text.
    2. Identifies snake_case and camelCase subwords.
    3. Flags explicit type-related suffixes (_str, _num, _id, etc.).
    4. Identifies promise/async/resource API patterns.
    """
    tokens = IDENTIFIER_REGEX.findall(code)
    
    subwords = []
    type_markers = []
    api_markers = []
    
    for tok in tokens:
        # Check type suffixes
        tok_lower = tok.lower()
        for sfx in KNOWN_TYPE_SUFFIXES:
            if tok_lower.endswith(sfx):
                type_markers.append(f"__TYPE_{sfx.upper()}__")
                break
                
        # Split camelCase
        camel_split = CAMEL_CASE_REGEX.sub(r'\1 \2', tok)
        # Split snake_case
        parts = camel_split.replace('_', ' ').split()
        for p in parts:
            p_clean = p.lower()
            if len(p_clean) > 1 and p_clean not in ('the', 'for', 'and', 'not'):
                subwords.append(f"__sub_{p_clean}__")
                
    # Detect async / then patterns
    if ".then(" in code or ".then (" in code:
        if ".catch(" not in code and ".catch (" not in code:
            api_markers.append("__UNHANDLED_THEN_PROMISE__")
            
    # Detect bare except
    if "except:" in code or "except :" in code:
        api_markers.append("__BARE_EXCEPT__")

    # Combine original code with lexical semantic enrichment
    lexical_enrichment = " ".join(type_markers + subwords + api_markers)
    return f"{code}\n{lexical_enrichment}"

if __name__ == "__main__":
    test_py = "def sanitize_handlers(prefix_str, id_num):\n    return prefix_str + '_' + id_num"
    test_js = "function verify_buffer(hookUrl) {\n    dispatchWebhook(hookUrl).then((records) => {\n        console.log('Processed:', records);\n    });\n}"
    
    print("--- Python Test ---")
    print(extract_channel_b_lexical(test_py, "python"))
    print("\n--- JavaScript Test ---")
    print(extract_channel_b_lexical(test_js, "javascript"))

