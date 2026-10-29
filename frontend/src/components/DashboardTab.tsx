import React from 'react';
import type { AnalysisResult } from '../types';
import { 
  AlertTriangle, ShieldAlert, KeyRound, Bug, 
  GitCommit, Clock, CheckCircle, ExternalLink, ArrowRight, ShieldCheck, Cpu
} from 'lucide-react';

interface DashboardTabProps {
  data: AnalysisResult;
  onSelectTab: (tab: string) => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({ data, onSelectTab }) => {
  const { risk_overview, vulnerabilities_by_severity } = data;

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-severity-critical border-severity-critical/40 bg-severity-critical/10';
    if (score >= 40) return 'text-severity-high border-severity-high/40 bg-severity-high/10';
    if (score >= 20) return 'text-severity-medium border-severity-medium/40 bg-severity-medium/10';
    return 'text-severity-low border-severity-low/40 bg-severity-low/10';
  };

  return (
    <div className="space-y-6">
      {/* Target Repo Metadata Strip */}
      <div className="bg-surface/90 border border-surface-elevated rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-text-primary font-mono tracking-tight">{data.repo_name}</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-brand-violet/20 text-brand-violet border border-brand-violet/30">
              {data.repo_url.startsWith('fixture://') ? 'Verified Test Fixture' : 'Public GitHub Repo'}
            </span>
          </div>
          <div className="flex items-center space-x-4 text-xs text-text-secondary font-mono">
            <span className="flex items-center gap-1.5">
              <GitCommit className="w-3.5 h-3.5 text-brand-cyan" /> Commit: {data.commit_sha.slice(0, 8)}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-text-secondary" /> Analyzed: {data.analyzed_at}
            </span>
          </div>
        </div>

        {/* Action Button for Remediation */}
        {data.remediations.length > 0 && (
          <button
            onClick={() => onSelectTab('remediation')}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-brand-violet to-brand-cyan text-white text-xs font-bold uppercase tracking-wider shadow-lg shadow-brand-violet/25 hover:opacity-95 transition-all"
          >
            <span>Review {data.remediations.length} Safe Fix{data.remediations.length > 1 ? 'es' : ''}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Main Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Risk Score Card */}
        <div className="bg-surface border border-surface-elevated rounded-2xl p-5 relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-text-secondary">Composite Risk</span>
            <span className={`px-2 py-0.5 rounded text-[11px] font-bold font-mono border ${getScoreColor(risk_overview.score)}`}>
              {risk_overview.label}
            </span>
          </div>
          <div className="flex items-baseline space-x-2 my-2">
            <span className="text-4xl font-black font-mono text-text-primary">{risk_overview.score}</span>
            <span className="text-sm font-mono text-text-secondary">/100</span>
          </div>
          <div className="w-full bg-surface-elevated rounded-full h-2 mt-3 overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-700 ${
                risk_overview.score >= 70 ? 'bg-severity-critical' : risk_overview.score >= 40 ? 'bg-severity-high' : 'bg-severity-low'
              }`}
              style={{ width: `${Math.min(100, Math.max(5, risk_overview.score))}%` }}
            />
          </div>
          <p className="text-[11px] text-text-secondary mt-2 line-clamp-2">
            Deterministic formula factoring CVSS, CISA KEV weaponization, and reachability.
          </p>
        </div>

        {/* Components & SBOM */}
        <div 
          onClick={() => onSelectTab('sbom')}
          className="bg-surface border border-surface-elevated rounded-2xl p-5 hover:border-brand-cyan/40 transition-all cursor-pointer shadow-lg group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-text-secondary">SBOM Inventory</span>
            <Cpu className="w-4 h-4 text-brand-cyan group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-4xl font-black font-mono text-text-primary my-2">
            {data.total_components}
          </div>
          <p className="text-xs text-brand-cyan font-mono flex items-center gap-1 mt-3">
            <span>Inspect CycloneDX / SPDX</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </p>
        </div>

        {/* Vulnerabilities Breakdown */}
        <div 
          onClick={() => onSelectTab('vulnerabilities')}
          className="bg-surface border border-surface-elevated rounded-2xl p-5 hover:border-brand-violet/40 transition-all cursor-pointer shadow-lg group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-text-secondary">Total Vulnerabilities</span>
            <Bug className="w-4 h-4 text-severity-critical group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-4xl font-black font-mono text-text-primary my-2">
            {data.vulnerabilities.length}
          </div>
          <div className="flex items-center space-x-2 mt-3 text-[11px] font-mono">
            <span className="text-severity-critical font-bold">{vulnerabilities_by_severity.CRITICAL || 0} Crit</span>
            <span className="text-text-secondary">•</span>
            <span className="text-severity-high font-bold">{vulnerabilities_by_severity.HIGH || 0} High</span>
            <span className="text-text-secondary">•</span>
            <span className="text-severity-medium">{vulnerabilities_by_severity.MEDIUM || 0} Med</span>
          </div>
        </div>

        {/* Credential Leaks */}
        <div 
          onClick={() => onSelectTab('secrets')}
          className="bg-surface border border-surface-elevated rounded-2xl p-5 hover:border-brand-cyan/40 transition-all cursor-pointer shadow-lg group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-text-secondary">Leaked Secrets</span>
            <KeyRound className="w-4 h-4 text-brand-cyan group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-4xl font-black font-mono text-text-primary my-2">
            {data.secret_findings_count}
          </div>
          <p className="text-xs text-text-secondary mt-3">
            {data.secret_findings_count > 0 ? (
              <span className="text-severity-critical font-bold flex items-center gap-1 font-mono">
                <AlertTriangle className="w-3.5 h-3.5" /> Redacted & Rotation Required
              </span>
            ) : (
              <span className="text-severity-low flex items-center gap-1 font-mono">
                <CheckCircle className="w-3.5 h-3.5" /> No Leaked Secrets Detected
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Critical Attention Box & Remediation Callout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Urgent Findings */}
        <div className="lg:col-span-2 bg-surface border border-surface-elevated rounded-2xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-severity-critical" />
              Critical Security Findings Requiring Action
            </h3>
            <span className="text-xs text-text-secondary font-mono">
              {data.vulnerabilities.filter(v => v.cisa_kev || v.severity === 'CRITICAL').length} High Priority
            </span>
          </div>

          <div className="space-y-3">
            {data.vulnerabilities.filter(v => v.cisa_kev || v.severity === 'CRITICAL').slice(0, 3).map((vuln) => (
              <div 
                key={vuln.id}
                className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-elevated hover:border-brand-violet/40 transition-colors flex items-start justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-text-primary text-xs">{vuln.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-severity-critical/20 text-severity-critical border border-severity-critical/30">
                      {vuln.severity}
                    </span>
                    {vuln.cisa_kev && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-severity-critical text-white shadow-sm">
                        CISA KEV WEAPONIZED
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-secondary line-clamp-1">{vuln.explanation}</p>
                  <p className="text-[11px] font-mono text-brand-cyan">
                    Package: <span className="font-bold">{vuln.package}</span> ({vuln.affected_version}) → Fix: <span className="text-severity-low font-bold">{vuln.fixed_version || 'Investigation required'}</span>
                  </p>
                </div>

                <button
                  onClick={() => onSelectTab('vulnerabilities')}
                  className="px-3 py-1.5 rounded-lg bg-surface text-text-primary text-xs font-mono hover:bg-brand-violet/20 hover:text-brand-violet transition-colors shrink-0"
                >
                  Details
                </button>
              </div>
            ))}

            {data.vulnerabilities.length === 0 && (
              <div className="p-8 text-center text-text-secondary text-xs font-mono bg-surface-elevated/30 rounded-xl">
                <ShieldCheck className="w-8 h-8 text-severity-low mx-auto mb-2 opacity-80" />
                No critical vulnerabilities detected in this component inventory.
              </div>
            )}
          </div>
        </div>

        {/* Explainable Scoring Summary Box */}
        <div className="bg-surface border border-surface-elevated rounded-2xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary mb-3">
              Explainable Risk Breakdown
            </h3>
            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              {risk_overview.summary_explanation}
            </p>

            <div className="space-y-2.5 font-mono text-xs">
              <div className="flex justify-between items-center py-1 border-b border-surface-elevated text-text-secondary">
                <span>CVSS Base Severity:</span>
                <span className="text-text-primary font-bold">{data.risk_overview.breakdown.max_vulnerability_score?.toFixed(1) || '0.0'}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-surface-elevated text-text-secondary">
                <span>CISA KEV Weaponized:</span>
                <span className={data.risk_overview.breakdown.cisa_kev_active ? 'text-severity-critical font-bold' : 'text-text-secondary'}>
                  {data.risk_overview.breakdown.cisa_kev_active ? 'Active Override (+25)' : 'None'}
                </span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-surface-elevated text-text-secondary">
                <span>Credential Leaks Penalty:</span>
                <span className="text-text-primary font-bold">+{data.risk_overview.breakdown.secret_risk_penalty?.toFixed(1) || '0.0'}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-surface-elevated text-text-secondary">
                <span>Suspicious Heuristics:</span>
                <span className="text-text-primary font-bold">+{data.risk_overview.breakdown.suspicious_dependency_penalty?.toFixed(1) || '0.0'}</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-surface-elevated flex items-center justify-between">
            <span className="text-xs text-text-secondary font-mono">Confidence Level:</span>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40">
              HIGH (Authoritative)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
