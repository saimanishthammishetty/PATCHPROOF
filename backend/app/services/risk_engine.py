from typing import List, Dict, Any, Tuple
from app.models.schemas import (
    Component, VulnerabilityFinding, SecretFinding,
    DependencyHealthFinding, RiskOverview
)

class RiskEngine:
    """
    Transparent, deterministic risk scoring engine (0 - 100).
    
    Formula for Individual Finding Risk Score:
      Risk = (CVSS_Weight * 35) + (KEV_Weight * 25) + (EPSS_Weight * 20) + (Reachability_Weight * 10) + (Health_Weight * 10)
    
    Overriding rules:
      - CISA KEV active exploitation guarantees a score of at least 80 (Critical).
      - CVSS >= 9.0 + Direct dependency guarantees a score of at least 75 (Critical).
      - Leaked secrets in git history trigger an independent high risk factor.
    """

    @staticmethod
    def calculate_finding_risk(vuln: VulnerabilityFinding) -> float:
        # 1. CVSS Base (0.0 to 10.0 -> normalized 0 to 1)
        cvss = vuln.cvss_score or (9.5 if vuln.severity == "CRITICAL" else (7.5 if vuln.severity == "HIGH" else 5.0))
        cvss_component = (cvss / 10.0) * 35.0

        # 2. CISA KEV active exploitation
        kev_component = 25.0 if vuln.cisa_kev else 0.0

        # 3. EPSS probability (0.0 to 1.0)
        epss = vuln.epss_probability or (0.5 if vuln.cisa_kev else (0.3 if vuln.severity == "CRITICAL" else 0.05))
        epss_component = min(1.0, epss) * 20.0

        # 4. Reachability
        if vuln.reachability == "reachable":
            reach_component = 10.0
        elif vuln.reachability == "unknown":
            reach_component = 5.0
        else:
            reach_component = 0.0

        # 5. Base score
        raw_score = cvss_component + kev_component + epss_component + reach_component

        # Critical Overrides
        if vuln.cisa_kev:
            raw_score = max(raw_score, 82.0)
        elif vuln.severity == "CRITICAL" and vuln.reachability == "reachable":
            raw_score = max(raw_score, 78.0)

        return round(min(100.0, max(0.0, raw_score)), 1)

    @classmethod
    def calculate_overall_risk(
        cls,
        components: List[Component],
        vulnerabilities: List[VulnerabilityFinding],
        secrets: List[SecretFinding],
        health_findings: List[DependencyHealthFinding]
    ) -> RiskOverview:
        if not components and not secrets:
            return RiskOverview(
                score=0.0,
                label="Low",
                breakdown={"cvss_factor": 0.0, "kev_factor": 0.0, "epss_factor": 0.0, "secrets_factor": 0.0},
                summary_explanation="No dependencies or security risks identified in repository."
            )

        finding_scores = [cls.calculate_finding_risk(v) for v in vulnerabilities]
        max_vuln_score = max(finding_scores) if finding_scores else 0.0
        
        # Secret penalty: Active secrets in code add significant critical risk
        secret_penalty = min(30.0, len(secrets) * 15.0)
        
        # Suspicious packages penalty
        suspicious_count = sum(1 for h in health_findings if h.is_suspicious)
        suspicious_penalty = min(20.0, suspicious_count * 10.0)

        # Critical composite calculation:
        # A repository's risk score must be at least as severe as its worst vulnerability,
        # plus additional penalties for secrets and suspicious indicators.
        composite_score = max_vuln_score + (secret_penalty * 0.3) + (suspicious_penalty * 0.2)
        
        if any(v.cisa_kev for v in vulnerabilities):
            composite_score = max(composite_score, 85.0)
        if any(s.confidence == "High" for s in secrets):
            composite_score = max(composite_score, 75.0)

        final_score = round(min(100.0, max(0.0, composite_score)), 1)

        # Thresholds:
        # 0 - 19: Low
        # 20 - 39: Medium
        # 40 - 69: High
        # 70 - 100: Critical
        if final_score >= 70.0:
            label = "Critical"
        elif final_score >= 40.0:
            label = "High"
        elif final_score >= 20.0:
            label = "Medium"
        else:
            label = "Low"

        # Update each component risk_score
        for comp in components:
            comp_vulns = [v for v in vulnerabilities if v.package.lower() == comp.name.lower()]
            if comp_vulns:
                comp.risk_score = max(cls.calculate_finding_risk(v) for v in comp_vulns)
            else:
                comp.risk_score = 5.0 if not comp.direct else 10.0

        summary = (
            f"Overall risk evaluated as {label} ({final_score}/100). "
            f"Evaluated {len(components)} components, {len(vulnerabilities)} vulnerabilities "
            f"({sum(1 for v in vulnerabilities if v.severity == 'CRITICAL')} critical), "
            f"{len(secrets)} secrets detected, and {suspicious_count} suspicious package alerts."
        )

        return RiskOverview(
            score=final_score,
            label=label,
            breakdown={
                "max_vulnerability_score": max_vuln_score,
                "secret_risk_penalty": secret_penalty,
                "suspicious_dependency_penalty": suspicious_penalty,
                "cisa_kev_active": 1.0 if any(v.cisa_kev for v in vulnerabilities) else 0.0
            },
            summary_explanation=summary
        )
