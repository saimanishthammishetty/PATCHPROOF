"""
PATCHPROOF Phase O.1 — Quarantine Policy Validation Test Suite & Offline Simulation.
Runs synthetic unit tests and performs a complete simulation on the local Big-Vul Arrow cache.
Strict Safety:
  - Zero data acquisition.
  - Zero modifications to train, val, test, or robust datasets.
  - Preserves NEVER_MERGE_ACTIVE.
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple, Set, Optional

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.experiments.experiment_o.quarantine_policy import (
    QuarantinePolicyEngine, QuarantineVerdict, compute_exact_sha256,
    compute_normalized_sha256, compute_ast_sha256
)

def run_synthetic_tests() -> Dict[str, Any]:
    print("=" * 80)
    print("RUNNING PHASE O.1 SYNTHETIC QUARANTINE POLICY UNIT TESTS")
    print("=" * 80)

    # Base reference function to seed exclusions
    ref_code = """
    int calculate_checksum(const unsigned char *data, size_t len) {
        int sum = 0;
        for (size_t i = 0; i < len; i++) {
            sum = (sum + data[i]) & 0xFFFF;
        }
        return sum;
    }
    """
    ref_exact = compute_exact_sha256(ref_code)
    ref_norm = compute_normalized_sha256(ref_code)
    ref_ast, _ = compute_ast_sha256(ref_code)

    # Create engine with mocked exclusion database
    engine = QuarantinePolicyEngine(
        exact_exclusions={ref_exact},
        norm_exclusions={ref_norm},
        ast_exclusions={ref_ast} if ref_ast else set(),
        commit_exclusions={"d3adb33f12345678", "c0mm1t9876543210"},
        template_exclusions={"ssl/ssl_lib.c::ssl_free", "tmpl::synthetic_buffer_mutation"}
    )

    test_cases = [
        {
            "id": "TC-01",
            "name": "Exact SHA-256 duplicate rejection",
            "candidate": {
                "repository": "openssl/openssl",
                "original_code": ref_code,
                "is_vulnerable": True,
                "cve_id": "CVE-2021-3712",
                "cwe_id": "CWE-125",
                "commit_hash": "a1b2c3d4e5f67890"
            },
            "expected_decision": "REJECTED_EXACT_CODE_DUPLICATE",
            "expected_status": "REJECTED"
        },
        {
            "id": "TC-02",
            "name": "Whitespace & comment variation (Normalized-code duplicate)",
            "candidate": {
                "repository": "openssl/openssl",
                "original_code": """
                /* Calculates the checksum of buffer */
                int   calculate_checksum  ( const unsigned char *data , size_t len )   {
                    // initialize sum
                    int sum = 0 ;
                    for ( size_t i = 0 ; i < len ; i++ ) {
                        sum = ( sum + data [ i ] ) & 0xFFFF ;
                    }
                    return sum ;
                }
                """,
                "is_vulnerable": True,
                "cve_id": "CVE-2021-3712",
                "cwe_id": "CWE-125",
                "commit_hash": "a1b2c3d4e5f67890"
            },
            "expected_decision": "REJECTED_NORMALIZED_CODE_DUPLICATE",
            "expected_status": "REJECTED"
        },
        {
            "id": "TC-03",
            "name": "Renamed local identifiers (AST-equivalent code)",
            "candidate": {
                "repository": "openssl/openssl",
                "original_code": """
                int calculate_checksum(const unsigned char *buf_ptr, size_t n_bytes) {
                    int acc = 0;
                    for (size_t idx = 0; idx < n_bytes; idx++) {
                        acc = (acc + buf_ptr[idx]) & 0xFFFF;
                    }
                    return acc;
                }
                """,
                "is_vulnerable": True,
                "cve_id": "CVE-2021-3712",
                "cwe_id": "CWE-125",
                "commit_hash": "a1b2c3d4e5f67890"
            },
            "expected_decision": "REJECTED_AST_EQUIVALENT",
            "expected_status": "REJECTED"
        },
        {
            "id": "TC-04",
            "name": "Same-commit distinct function (Eligible for Manual Review, Never Auto-Accepted)",
            "candidate": {
                "repository": "openssl/openssl",
                "original_code": """
                int parse_tls_extension(SSL *s, const unsigned char *in, size_t in_len) {
                    if (in == NULL || in_len < 4) return 0;
                    uint16_t ext_type = (in[0] << 8) | in[1];
                    uint16_t ext_len = (in[2] << 8) | in[3];
                    if (in_len - 4 < ext_len) return -1;
                    return (int)ext_type;
                }
                """,
                "is_vulnerable": True,
                "cve_id": "CVE-2022-0778",
                "cwe_id": "CWE-835",
                "commit_hash": "d3adb33f12345678"  # Known commit in commit_exclusions
            },
            "expected_decision": "FLAGGED_SAME_COMMIT_MANUAL_REVIEW_REQUIRED",
            "expected_status": "FLAGGED_MANUAL_REVIEW"
        },
        {
            "id": "TC-05",
            "name": "Missing or ambiguous vulnerability CVE provenance",
            "candidate": {
                "repository": "wireshark/wireshark",
                "original_code": """
                int dissect_custom_proto(tvbuff_t *tvb, packet_info *pinfo, proto_tree *tree) {
                    if (tvb_reported_length(tvb) < 8) return 0;
                    return 8;
                }
                """,
                "is_vulnerable": True,
                "cve_id": None,  # Missing CVE
                "cwe_id": "CWE-119",
                "commit_hash": "feedbeef11223344"
            },
            "expected_decision": "REJECTED_MISSING_OR_AMBIGUOUS_PROVENANCE",
            "expected_status": "REJECTED"
        },
        {
            "id": "TC-06",
            "name": "Offline unavailable repository (nginx marked UNAVAILABLE_OFFLINE)",
            "candidate": {
                "repository": "nginx/nginx",
                "original_code": """
                ngx_int_t ngx_http_handler(ngx_http_request_t *r) {
                    return NGX_OK;
                }
                """,
                "is_vulnerable": False,
                "commit_hash": "778899aabbccddeeff"
            },
            "expected_decision": "REJECTED_SOURCE_UNAVAILABLE_OFFLINE",
            "expected_status": "REJECTED"
        },
        {
            "id": "TC-07",
            "name": "Offline unavailable repository (sqlite marked UNAVAILABLE_OFFLINE)",
            "candidate": {
                "repository": "sqlite/sqlite",
                "original_code": """
                int sqlite3_step(sqlite3_stmt *pStmt) {
                    return 0;
                }
                """,
                "is_vulnerable": False,
                "commit_hash": "aabbccddeeff001122"
            },
            "expected_decision": "REJECTED_SOURCE_UNAVAILABLE_OFFLINE",
            "expected_status": "REJECTED"
        },
        {
            "id": "TC-08",
            "name": "Mandatory excluded repository (QEMU / FFmpeg)",
            "candidate": {
                "repository": "devign/qemu",
                "original_code": """
                void qemu_device_reset(void *opaque) {
                    return;
                }
                """,
                "is_vulnerable": False,
                "commit_hash": "1122334455667788"
            },
            "expected_decision": "REJECTED_REPOSITORY_QEMU_FFMPEG",
            "expected_status": "REJECTED"
        },
        {
            "id": "TC-09",
            "name": "Clean code failing deterministic static analysis (Returning stack address)",
            "candidate": {
                "repository": "curl/curl",
                "original_code": """
                char *create_local_header(const char *name) {
                    char local_arr[128];
                    return local_arr;
                }
                """,
                "is_vulnerable": False,
                "commit_hash": "9988776655443322"
            },
            "expected_decision": "REJECTED_CLEAN_FAILED_STATIC_ANALYSIS",
            "expected_status": "REJECTED"
        },
        {
            "id": "TC-10",
            "name": "Valid clean function with full provenance & passing static analysis",
            "candidate": {
                "repository": "curl/curl",
                "original_code": """
                int safe_str_copy(char *dest, size_t dest_sz, const char *src) {
                    if (dest == NULL || src == NULL || dest_sz == 0) return -1;
                    size_t i = 0;
                    while (i < dest_sz - 1 && src[i] != '\\0') {
                        dest[i] = src[i];
                        i++;
                    }
                    dest[i] = '\\0';
                    return (int)i;
                }
                """,
                "is_vulnerable": False,
                "commit_hash": "8877665544332211"
            },
            "expected_decision": "ACCEPTED_CLEAN_BENCHMARK_CANDIDATE",
            "expected_status": "ACCEPTED"
        },
        {
            "id": "TC-11",
            "name": "Valid vulnerable function with verified CVE, commit, and CWE",
            "candidate": {
                "repository": "redis/redis",
                "original_code": """
                void process_resp_buffer(char *buf, size_t len) {
                    char target[64];
                    memcpy(target, buf, len);
                }
                """,
                "is_vulnerable": True,
                "cve_id": "CVE-2023-45145",
                "cwe_id": "CWE-119",
                "commit_hash": "3344556677889900"
            },
            "expected_decision": "ACCEPTED_VULNERABLE_BENCHMARK_CANDIDATE",
            "expected_status": "ACCEPTED"
        }
    ]

    test_results = []
    passed_all = True
    for tc in test_cases:
        verdict = engine.evaluate_candidate(tc["candidate"])
        status_match = (verdict.status == tc["expected_status"])
        decision_match = (verdict.decision_code == tc["expected_decision"])
        test_passed = status_match and decision_match
        if not test_passed:
            passed_all = False

        res_entry = {
            "test_id": tc["id"],
            "test_name": tc["name"],
            "expected_status": tc["expected_status"],
            "actual_status": verdict.status,
            "expected_decision": tc["expected_decision"],
            "actual_decision": verdict.decision_code,
            "test_passed": test_passed,
            "reason": verdict.reason
        }
        test_results.append(res_entry)
        print(f"  [{'PASS' if test_passed else 'FAIL'}] {tc['id']}: {tc['name']}")
        if not test_passed:
            print(f"       Expected: {tc['expected_decision']} ({tc['expected_status']})")
            print(f"       Actual:   {verdict.decision_code} ({verdict.status})")

    assert passed_all, "One or more synthetic unit tests failed!"
    print(f"\n[SUCCESS] All {len(test_cases)} synthetic unit tests PASSED.\n")
    return {
        "unit_test_summary": {
            "total_tests": len(test_cases),
            "passed": len([t for t in test_results if t["test_passed"]]),
            "failed": len([t for t in test_results if not t["test_passed"]]),
            "status": "ALL_TESTS_PASSED" if passed_all else "FAILURES_DETECTED"
        },
        "test_cases": test_results
    }

def run_quarantine_simulation() -> Dict[str, Any]:
    print("=" * 80)
    print("RUNNING PHASE O.1 QUARANTINE POLICY SIMULATION ON LOCAL BIG-VUL ARROW CACHE")
    print("=" * 80)

    # 1. Load actual historical exclusions from processed splits
    print("[INIT] Loading real exclusion databases from existing processed datasets...")
    engine = QuarantinePolicyEngine.load_from_processed_splits(ROOT_DIR)
    print(f"  Loaded {len(engine.exact_exclusions):,} exact SHA-256 exclusions.")
    print(f"  Loaded {len(engine.norm_exclusions):,} normalized SHA-256 exclusions.")
    print(f"  Loaded {len(engine.commit_exclusions):,} commit hash exclusions.")
    print(f"  Loaded {len(engine.template_exclusions):,} template / function signature exclusions.")

    # 2. Open Big-Vul arrow cache
    base_arrow = Path("C:/Users/Dell/.cache/huggingface/datasets/bstee615___bigvul/default/0.0.0/4d8647a9b52fdd2ae42343c60fd6c7c48bbff25e")
    assert base_arrow.exists(), f"Big-Vul arrow cache not found at {base_arrow}"

    from datasets import Dataset
    import pyarrow.compute as pc

    target_projects = ["linux", "openssl", "wireshark", "curl", "redis", "nginx", "sqlite"]
    simulation_counts = {
        "total_evaluated": 0,
        "by_status": Counter(),
        "by_decision_code": Counter(),
        "by_repository": defaultdict(lambda: Counter()),
        "vulnerable_by_cwe": Counter(),
        "flagged_same_commit_distinct_functions": []
    }

    print("\n[SIMULATION] Evaluating offline candidates across 7 target repositories...")
    for repo in target_projects:
        # Check offline availability
        if repo in ("nginx", "sqlite"):
            # Synthetic placeholder evaluation to record UNAVAILABLE_OFFLINE
            dummy_candidate = {
                "repository": repo,
                "original_code": "int dummy() { return 0; }",
                "is_vulnerable": False,
                "commit_hash": "00000000"
            }
            v = engine.evaluate_candidate(dummy_candidate)
            simulation_counts["total_evaluated"] += 1
            simulation_counts["by_status"][v.status] += 1
            simulation_counts["by_decision_code"][v.decision_code] += 1
            simulation_counts["by_repository"][repo][v.decision_code] += 1
            print(f"  [{repo.upper()}] Status: {v.decision_code}")
            continue

        repo_evaluated = 0
        repo_accepted = 0
        repo_flagged = 0
        repo_rejected = 0

        for split in ["train", "validation", "test"]:
            arrow_file = base_arrow / f"bigvul-{split}.arrow"
            ds = Dataset.from_file(str(arrow_file))
            table = ds.data.table
            p_mask = pc.equal(pc.utf8_lower(table["project"]), repo)
            sub = table.filter(p_mask)

            for row in sub.to_pylist():
                is_vul = (row.get("vul") == 1)
                code = row.get("func_before") if is_vul else row.get("func_after")
                cve = row.get("CVE ID")
                cwe = row.get("CWE ID")
                commit = row.get("commit_id")

                cand = {
                    "repository": repo,
                    "original_code": code,
                    "is_vulnerable": is_vul,
                    "cve_id": cve,
                    "cwe_id": cwe,
                    "commit_hash": commit,
                    "file_path": row.get("codeLink", ""),
                    "function_name": ""
                }

                verdict = engine.evaluate_candidate(cand)
                simulation_counts["total_evaluated"] += 1
                simulation_counts["by_status"][verdict.status] += 1
                simulation_counts["by_decision_code"][verdict.decision_code] += 1
                simulation_counts["by_repository"][repo][verdict.decision_code] += 1
                repo_evaluated += 1

                if verdict.status == "ACCEPTED":
                    repo_accepted += 1
                    if is_vul and cwe:
                        simulation_counts["vulnerable_by_cwe"][cwe] += 1
                elif verdict.status == "FLAGGED_MANUAL_REVIEW":
                    repo_flagged += 1
                    if len(simulation_counts["flagged_same_commit_distinct_functions"]) < 10:
                        simulation_counts["flagged_same_commit_distinct_functions"].append({
                            "repository": repo,
                            "cve_id": cve,
                            "cwe_id": cwe,
                            "commit_hash": commit,
                            "is_vulnerable": is_vul,
                            "code_snippet": (code or "")[:120].replace("\n", " ")
                        })
                else:
                    repo_rejected += 1

        print(f"  [{repo:10s}] Total Eval: {repo_evaluated:5d} | Accepted: {repo_accepted:4d} | Flagged (Same Commit): {repo_flagged:4d} | Rejected: {repo_rejected:5d}")

    return simulation_counts

def main():
    start_time = time.time()
    unit_test_data = run_synthetic_tests()
    simulation_data = run_quarantine_simulation()
    duration = time.time() - start_time

    # Prepare simulation deliverable data
    out_dir = ROOT_DIR / "models" / "experiments" / "experiment_o"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. phase_o1_quarantine_policy.json
    policy_doc = {
        "policy_name": "PATCHPROOF Phase O.1 Multi-Tier Quarantine Policy",
        "policy_version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "decisions_enforced": {
            "decision_1": "Function-level deduplication is the primary exclusion policy.",
            "decision_2": "Exact SHA-256 duplicates are strictly REJECTED (REJECTED_EXACT_CODE_DUPLICATE).",
            "decision_3": "Normalized-code duplicates (whitespace, comments, identifiers) are strictly REJECTED (REJECTED_NORMALIZED_CODE_DUPLICATE).",
            "decision_4": "AST-equivalent functions are strictly REJECTED where reliable AST parsing is available (REJECTED_AST_EQUIVALENT).",
            "decision_5": "Same-function and template-family overlaps are strictly REJECTED (REJECTED_FUNCTION_TEMPLATE_OVERLAP).",
            "decision_6": "Same-commit distinct functions are FLAGGED_MANUAL_REVIEW. They are NEVER automatically accepted (FLAGGED_SAME_COMMIT_MANUAL_REVIEW_REQUIRED).",
            "decision_7": "Missing or ambiguous vulnerability provenance results in immediate rejection (REJECTED_MISSING_OR_AMBIGUOUS_PROVENANCE).",
            "decision_8": "nginx and SQLite are designated UNAVAILABLE_OFFLINE without live network or offline archives (REJECTED_SOURCE_UNAVAILABLE_OFFLINE)."
        },
        "tier_hierarchy": [
            "Tier 1: Offline Source Availability Check (nginx / sqlite marked UNAVAILABLE_OFFLINE)",
            "Tier 2: Excluded Repositories (QEMU / FFmpeg mandatory exclusion)",
            "Tier 3: Syntax & Format Validity (Length 30-6000 chars, braces, parentheses)",
            "Tier 4: Provenance Verification (Valid CVE, CWE, commit for vul; release & static analysis for clean)",
            "Tier 5: Exact SHA-256 Deduplication (Collision check against 112,635 hashes)",
            "Tier 6: Normalized AST Deduplication (Collision check against 112,605 hashes)",
            "Tier 7: Scope-Aware AST Canonical Equivalence (pycparser scope visitor)",
            "Tier 8: Function Signature & Template Family Overlap Check",
            "Tier 9: Same-Commit Distinct Function Flagging (Manual Review Gatekeeper)"
        ]
    }
    with open(out_dir / "phase_o1_quarantine_policy.json", "w", encoding="utf-8") as f:
        json.dump(policy_doc, f, indent=2)

    # 2. phase_o1_quarantine_simulation.json
    sim_doc = {
        "simulation_name": "Phase O.1 Quarantine Policy Offline Simulation",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "duration_seconds": round(duration, 2),
        "total_records_evaluated": simulation_data["total_evaluated"],
        "status_breakdown": dict(simulation_data["by_status"]),
        "decision_code_breakdown": dict(simulation_data["by_decision_code"]),
        "per_repository_breakdown": {
            repo: dict(counts) for repo, counts in simulation_data["by_repository"].items()
        },
        "accepted_vulnerable_by_cwe": dict(simulation_data["vulnerable_by_cwe"]),
        "flagged_same_commit_sample_traces": simulation_data["flagged_same_commit_distinct_functions"]
    }
    with open(out_dir / "phase_o1_quarantine_simulation.json", "w", encoding="utf-8") as f:
        json.dump(sim_doc, f, indent=2)

    print("\n[SAVED] phase_o1_quarantine_policy.json")
    print("[SAVED] phase_o1_quarantine_simulation.json")
    print("\nSimulation complete. Proceeding to report writing...")

if __name__ == "__main__":
    main()
