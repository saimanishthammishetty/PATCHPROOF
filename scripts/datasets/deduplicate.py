import re
import hashlib
from typing import List, Tuple, Dict, Set
from scripts.datasets.schema import CodeDebuggingExample

class DatasetDeduplicator:
    """
    High-performance O(N) exact and MinHash locality-sensitive deduplication
    designed for 50,000–100,000 code-debugging examples.
    """

    @staticmethod
    def _normalize_tokens(code: str) -> str:
        # Strip comments and multi-spaces
        clean = re.sub(r'#.*|//.*|/\*.*?\*/', '', code, flags=re.DOTALL)
        clean = "".join(clean.split())
        return clean

    @staticmethod
    def _compute_shingles(norm_code: str, k: int = 5) -> Set[int]:
        if len(norm_code) < k:
            return {hash(norm_code)}
        shingles = set()
        for i in range(len(norm_code) - k + 1):
            sub = norm_code[i:i+k]
            shingles.add(int(hashlib.md5(sub.encode("utf-8")).hexdigest()[:8], 16))
        return shingles

    @classmethod
    def deduplicate(
        cls,
        examples: List[CodeDebuggingExample],
        near_dedup_threshold: float = 0.85
    ) -> Tuple[List[CodeDebuggingExample], int, int]:
        seen_exact_hashes: Set[str] = set()
        # Inverted index for fast candidate retrieval: bucket_id -> list of example_ids
        band_buckets: Dict[str, str] = {}
        shingle_cache: Dict[str, Set[int]] = {}

        retained: List[CodeDebuggingExample] = []
        exact_dupes = 0
        near_dupes = 0

        for ex in examples:
            norm_code = cls._normalize_tokens(ex.original_code)
            h = hashlib.sha256(f"{ex.language}:{norm_code}".encode("utf-8")).hexdigest()

            # 1. Exact Duplicate Elimination (O(1))
            if h in seen_exact_hashes:
                exact_dupes += 1
                continue
            seen_exact_hashes.add(h)

            shingles = cls._compute_shingles(norm_code, k=5)
            if not shingles:
                if not ex.duplicate_group_id:
                    ex.duplicate_group_id = ex.example_id
                retained.append(ex)
                continue

            # 2. MinHash Locality-Sensitive Hashing (4 bands)
            sorted_shingles = sorted(list(shingles))
            # Create 4 bucket keys from min values in quartiles
            q_len = max(1, len(sorted_shingles) // 4)
            b1 = sorted_shingles[0]
            b2 = sorted_shingles[min(q_len, len(sorted_shingles)-1)]
            b3 = sorted_shingles[min(2*q_len, len(sorted_shingles)-1)]
            b4 = sorted_shingles[min(3*q_len, len(sorted_shingles)-1)]
            band_key = f"{ex.language}:{b1}:{b2}:{b3}:{b4}"

            if band_key in band_buckets:
                candidate_id = band_buckets[band_key]
                candidate_shingles = shingle_cache.get(candidate_id, set())
                intersection = len(shingles & candidate_shingles)
                union = len(shingles | candidate_shingles)
                jaccard = (intersection / union) if union > 0 else 0.0

                if jaccard >= near_dedup_threshold:
                    near_dupes += 1
                    ex.duplicate_group_id = candidate_id
                    continue

            # Record candidate in bucket
            band_buckets[band_key] = ex.example_id
            shingle_cache[ex.example_id] = shingles
            if not ex.duplicate_group_id:
                ex.duplicate_group_id = ex.example_id
            retained.append(ex)

        return retained, exact_dupes, near_dupes
