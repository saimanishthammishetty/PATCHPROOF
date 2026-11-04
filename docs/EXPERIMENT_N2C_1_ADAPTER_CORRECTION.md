# PATCHPROOF — EXPERIMENT N2C.1: CONTROLLED BIG-VUL ADAPTER CORRECTION
## Audit Corrections, Provenance Integrity, and High-Fidelity Defect Extraction

> **Document Version:** 1.0.0 — Authoritative Verification & Correction Report  
> **Date:** 2026-11-04  
> **Status:** AUDIT COMPLETE & REVISED EXTRACTION EXECUTED  
> **Target Subsystem:** Big-Vul Targeted Adapter Subsystem (`C:\PATCHPROOF`)  
> **Production Model Integrity:** SHA-256 `5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20` (VERIFIED INTACT)  
> **Production Test Dataset Integrity:** SHA-256 `9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d` (VERIFIED INTACT)  
> **Robust Held-Out Dataset Integrity:** SHA-256 `e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1` (VERIFIED INTACT)  
> **Original Experiment N2C Artifacts:** Byte-for-byte verified identical to pre-run baseline  
> **Safety Invariant:** `NEVER_MERGE_ACTIVE` (Active & Enforced)  

---

## 1. Executive Summary & Audit Context

Experiment N2C demonstrated the feasibility of harvesting minority defect classes (`null_pointer`, `undefined_behavior`, `state_management`) from the locally cached 57.8 MB Big-Vul dataset (`data/raw/big_vul_real_15000.jsonl`) without external downloads. However, an independent audit identified six critical areas requiring correction:
1. **Unstable Source Identity:** Using CVE alone collapsed distinct functions within the same CVE/commit into identical IDs.
2. **Commit Identifier Sanitization:** Suffixes (e.g. `?w=1`) were stripped without preserving original commit strings.
3. **Overstated Verification Claims:** Assigning `verification_status="syntax_verified"` without running a parser/compiler, and hardcoding `faulty_line_numbers=[1]` without AST fault localization.
4. **Weak Semantic Guards:** Permitting generic tokens (e.g., `cleanup` or `thread`) to justify `resource_leak` or `state_management` without concrete lifecycle or synchronization primitives.
5. **Project-Name Language Assumptions:** Inferring C++ from repository names rather than evaluating syntax tokens before computing content hashes.
6. **Short Code Hashes:** Truncating deduplication hashes to 16 characters rather than preserving full 64-character SHA-256 strings.

In Experiment N2C.1, **`BigVulTargetedAdapterV2`** was designed, implemented, unit-tested, and executed. All outputs were written exclusively under `data/experiments/experiment_n2c_1/` while the original N2C files were cryptographically verified to be 100% untouched.

---

## 2. Input/Output Conservation & Extraction Accounting

The adapter processed all 15,000 records from `data/raw/big_vul_real_15000.jsonl` with strict mathematical conservation:

$$\text{Total Records (15,000)} = \text{Extracted Candidates (180)} + \text{Quarantined Records (14,820)}$$

```
+------------------------------------------+-----------------------+-----------------------+
| Metric Dimension                         | Experiment N2C (v1)   | Experiment N2C.1 (v2) |
+------------------------------------------+-----------------------+-----------------------+
| Total Input Records                      | 15,000                | 15,000                |
| Valid Candidates Extracted               | 409 (weak semantic)   | **180 (high-fidelity)**|
| Quarantined Records                      | 14,591                | **14,820**            |
| Deduplication Code Collisions            | 0                     | 0 (all distinct code) |
| Input / Output Conservation              | 100% (409 + 14,591)   | **100% (180 + 14,820)**|
| Unique Source-Row Identities             | N/A (collapsed by CVE)| **180 (1 per row)**   |
| Unique CVE Identifiers                   | 157                   | **124**               |
| Unique Real-World Projects               | 53                    | **43**                |
| Unique Indivisible Isolation Groups      | 157                   | **131**               |
+------------------------------------------+-----------------------+-----------------------+
```

---

## 3. High-Fidelity 13-Class Distribution

Under strengthened semantic validation, ambiguous records lacking concrete proof of vulnerability mechanics were quarantined. The resulting candidate corpus consists exclusively of high-confidence real-world defects:

```
+---------------------------+-----------------------+-----------------------+------------------------------------------+
| Defect Category           | N2C (v1) Count        | N2C.1 (v2) Count      | Semantic Validation Requirement Applied  |
+---------------------------+-----------------------+-----------------------+------------------------------------------+
| `null_pointer` (CWE-476)  | 137                   | **108**               | Pointer dereference + NULL comparison or |
|                           |                       |                       | pointer return context in function/patch |
+---------------------------+-----------------------+-----------------------+------------------------------------------+
| `undefined_behavior`      | 183                   | **61**                | Integer arithmetic + integer types +     |
| (CWE-190)                 |                       |                       | concrete overflow bounds/alloc evidence  |
+---------------------------+-----------------------+-----------------------+------------------------------------------+
| `state_management`        | 89                    | **11**                | Concurrency primitives (mutex, spinlock, |
| (CWE-362)                 |                       |                       | atomic) + shared state race mechanics    |
+---------------------------+-----------------------+-----------------------+------------------------------------------+
| `resource_leak` (CWE-401) | 0 (0 in raw cache)    | **0** (supported)     | Allocation call (malloc/new) + missing   |
|                           |                       |                       | or patched deallocation (free/delete)    |
+---------------------------+-----------------------+-----------------------+------------------------------------------+
| Total Extracted           | 409                   | **180**               | All 180 validated against Pydantic schema|
+---------------------------+-----------------------+-----------------------+------------------------------------------+
```

### Representation of Top Open-Source Projects
The 180 validated candidates span 43 premier open-source C/C++ projects, adding 131 new independent commit-level isolation groups:
- **linux kernel:** 58 candidates (32.2%)
- **php-src:** 19 candidates (10.6%)
- **jasper:** 10 candidates (5.6%)
- **FreeRDP:** 6 candidates (3.3%)
- **Android:** 6 candidates (3.3%)
- **openssl:** 6 candidates (3.3%)
- **libxkbcommon:** 5 candidates (2.8%)
- **libgit2:** 5 candidates (2.8%)
- **ImageMagick:** 5 candidates (2.8%)
- **Chrome:** 4 candidates (2.2%)
- **qemu / FFmpeg / virglrenderer / radare2:** 16 candidates (8.9%)

---

## 4. Language Detection & Deduplication Integrity

### Pre-Hashing Language Detection
Language classification was executed prior to computing the content hash, evaluating code syntax directly rather than relying on project names:
- **C (`c`):** 153 candidates (85.0%)
- **C++ (`cpp`):** 27 candidates (15.0%) — identified via keywords (`class`, `namespace`, `template<`, `std::`, `nullptr`, `static_cast<`, `new`, `delete`).
- **Uncertain Language Classifications:** 1 candidate across the entire 180-sample set (defaulted conservatively to C).

### Full 64-Character SHA-256 Hashes
Normalized code hashing now incorporates the language prefix into full 64-character SHA-256 strings:
$$\text{Hash} = \text{SHA256}(\text{language} + ":" + \text{WhitespaceStripped}(\text{original\_code}))$$
- No 16-character truncation collisions.
- Duplicate removal verified: 0 duplicates in candidate set (all 180 code snippets represent distinct implementations).

---

## 5. Metadata, Provenance, and Licensing Integrity

### 1. Stable Source-Row Identity (`source_record_id`)
To prevent ID collisions across distinct functions sharing a CVE or commit, `source_record_id` is derived deterministically from:
$$\text{source\_record\_id} = \text{"bigvul\_row\_"} + \text{row\_number}_{06d} + \text{"\_"} + \text{cve\_id} + \text{"\_"} + \text{project} + \text{"\_"} + \text{normalized\_commit}_{8}$$
- Guaranteed 100% unique across all extracted rows.
- Preserves direct traceability back to the exact line number of `data/raw/big_vul_real_15000.jsonl`.

### 2. Commit Identifier Preservation
- `raw_commit_id`: Preserves exact raw source strings, including query parameters (e.g. `?w=1` or `#L10`), documented within `bug_description`.
- `commit_hash`: Normalized hex SHA-1 hash for git tooling compatibility.

### 3. Truthful Fault Localization & Verification Status
- **`faulty_line_numbers`:** Set strictly to `[]` (empty list). Elimination of fabricated `[1]` values; reflects honest lack of line-level localization in raw function-level data.
- **`verification_status`:** Set strictly to `"unverified_static"`. No false claims of `syntax_verified` without dynamic compiler execution.

### 4. License Metadata Accounting
- All 15,000 raw Big-Vul records contain `license: "Public-Domain"`.
- Preserved verbatim as source-provided metadata.
- Documented in report metadata: *"Source-provided unverified metadata preserved directly from raw dataset; not independently verified."*

---

## 6. Detailed Quarantine & Rejection Breakdown

A total of 14,820 records were routed to `data/experiments/experiment_n2c_1/unmapped_candidates.jsonl`:

```
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| Rejection Reason                           | Record Count          | Audit Rationale                                             |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| `NON_VULNERABLE_OR_CLEAN`                  | 7,500                 | Records where `is_vul == False` (clean controls)            |
| `UNSUPPORTED_CWE`                          | 6,972                 | Non-target CWEs (e.g. CWE-119 buffer overflow, CWE-20, etc.)|
| `AMBIGUOUS_SEMANTICS: CWE-190`             | 150                   | Integer arithmetic present, but lacking concrete overflow   |
|                                            |                       | boundary checks or undersized allocation evidence           |
| `AMBIGUOUS_SEMANTICS: CWE-362`             | 169                   | Tagged CWE-362, but lacking explicit synchronization        |
|                                            |                       | primitives (mutex, atomic, spinlock) or race mechanics      |
| `AMBIGUOUS_SEMANTICS: CWE-476`             | 29                    | Lacking pointer dereference or NULL context evidence        |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| Total Quarantined                          | 14,820                | 100% preserved in unmapped_candidates.jsonl with reasons   |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
```

---

## 7. Automated Test Suite Results

The automated test suite `scripts/datasets/adapters/test_bigvul_targeted_adapter_v2.py` was executed with 13 comprehensive tests:

```
test_c_cpp_classification_and_hash_consistency ... ok
test_commit_identifiers_containing_suffixes ... ok
test_deterministic_output ... ok
test_duplicate_normalized_code_detection ... ok
test_full_sha256_output ... ok
test_missing_license_metadata ... ok
test_multiple_functions_sharing_one_project_commit ... ok
test_multiple_source_rows_sharing_one_cve ... ok
test_no_fabricated_faulty_line ... ok
test_no_false_syntax_verified_status ... ok
test_original_n2c_outputs_unchanged ... ok
test_preservation_of_source_provided_license ... ok
test_weak_cwe401_and_cwe362_evidence_rejection ... ok

----------------------------------------------------------------------
Ran 13 tests in 0.062s - OK
```

In addition, regression test suites were verified:
- `test_bigvul_targeted_adapter.py` (v1 tests): **8 passed**.
- `test_experimental_stratified_group_split.py` (N1.1 splitter tests): **13 passed**.
- **Total Test Suite:** **34 passed, 0 failed**.

---

## 8. Cryptographic Proof of Production & Artifact Preservation

All protected files and prior experiment artifacts were verified before and after execution:

```
+---------------------------------------------+------------------------------------------------------------------+-------------------+
| Artifact Path                               | Verified SHA-256 Cryptographic Hash                              | Verification State|
+---------------------------------------------+------------------------------------------------------------------+-------------------+
| `models/bug_detector.joblib`                | 5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20 | UNTOUCHED         |
| `data/processed/test.jsonl`                 | 9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d | UNTOUCHED         |
| `data/processed/robust_heldout_test.jsonl`  | e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1 | UNTOUCHED         |
| `data/processed/train.jsonl`                | 6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad | UNTOUCHED         |
| `data/processed/val.jsonl`                  | 935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f | UNTOUCHED         |
| `scripts/datasets/split.py`                 | 9f04150c57023eabc76a638d3d29431292f1b0f629ee8ac9a94f2c7126705fcd | UNTOUCHED         |
| `scripts/datasets/experimental_strat...`    | 0851bc257de0fb05e846166e1c2c36a3aaf72bb1b5059169c1820b7c3518e6c6 | UNTOUCHED         |
+---------------------------------------------+------------------------------------------------------------------+-------------------+
| `data/experiments/experiment_n2c/cand...`   | 32d370f3fd3108923398ad3eabd75c4348dcba230126257d5b64a0cff8a1f8ae | UNTOUCHED (N2C)   |
| `data/experiments/experiment_n2c/quar...`   | 81b2022adb3742c5b5683a215c6969ef6db3b0cd5fcc9a250cee2ca267e24dde | UNTOUCHED (N2C)   |
| `data/experiments/experiment_n2c/repo...`   | 39a6b3d30a307e8c8cef5274dc7244855584588d530c6ad6004fdc89cbca856f | UNTOUCHED (N2C)   |
+---------------------------------------------+------------------------------------------------------------------+-------------------+
```

- **Zero model modifications or training operations conducted.**
- **Zero production dataset modifications conducted.**
- **Zero external network requests or dataset downloads conducted.**
- **Original Experiment N2C files preserved byte-for-byte.**
- **Safety invariant `NEVER_MERGE_ACTIVE` remains active and enforced.**

---

## 9. Generated Experiment N2C.1 Files

The following files were created for Experiment N2C.1:
1. [`scripts/datasets/adapters/bigvul_targeted_adapter_v2.py`](file:///C:/PATCHPROOF/scripts/datasets/adapters/bigvul_targeted_adapter_v2.py) — Corrected high-fidelity adapter.
2. [`scripts/datasets/adapters/test_bigvul_targeted_adapter_v2.py`](file:///C:/PATCHPROOF/scripts/datasets/adapters/test_bigvul_targeted_adapter_v2.py) — 13 unit tests covering all audit criteria.
3. [`data/experiments/experiment_n2c_1/bigvul_candidates.jsonl`](file:///C:/PATCHPROOF/data/experiments/experiment_n2c_1/bigvul_candidates.jsonl) — 180 validated defect candidate records.
4. [`data/experiments/experiment_n2c_1/unmapped_candidates.jsonl`](file:///C:/PATCHPROOF/data/experiments/experiment_n2c_1/unmapped_candidates.jsonl) — 14,820 quarantined records with detailed failure reasons.
5. [`data/experiments/experiment_n2c_1/extraction_report.json`](file:///C:/PATCHPROOF/data/experiments/experiment_n2c_1/extraction_report.json) — Machine-readable audit and statistics summary.
6. [`docs/EXPERIMENT_N2C_1_ADAPTER_CORRECTION.md`](file:///C:/PATCHPROOF/docs/EXPERIMENT_N2C_1_ADAPTER_CORRECTION.md) — Authoritative audit correction documentation.

---
*Report Author: Antigravity Autonomous Research Harness*  
*Repository: `C:\PATCHPROOF`*  
*Safety Invariant: `NEVER_MERGE_ACTIVE`*

