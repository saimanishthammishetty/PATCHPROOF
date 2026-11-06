import React, { useState } from 'react';
import type { AnalysisResult } from '../types';
import {
  AlertTriangle, ShieldAlert, KeyRound, Bug,
  GitCommit, Clock, CheckCircle, ExternalLink, ArrowRight,
  ShieldCheck, Cpu, Copy, Check, Sparkles, Layers, Shield
} from 'lucide-react';

interface DashboardTabProps {
  data: AnalysisResult;
  onSelectTab: (tab: string) => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({ data, onSelectTab }) => {
  const { risk_overview, vulnerabilities_by_severity } = data;
  const [copiedCommit, setCopiedCommit] = useState(false);

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-severity-critical border-severity-critical/40 bg-severity-critical/10';
    if (score >= 40) return 'text-severity-high border-severity-high/40 bg-severity-high/10';
    if (score >= 20) return 'text-severity-medium border-severity-medium/40 bg-severity-medium/10';
    return 'text-severity-low border-severity-low/40 bg-severity-low/10';
  };

  const copyCommit = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(data.commit_sha);
    setCopiedCommit(true);
    setTimeout(() => setCopiedCommit(false), 2000);
  };

  const directCount = data.components.filter(c => c.direct).length;
  const transitiveCount = data.components.length - directCount;

  return (
    <div className="space-y-6">
      {/* Target Repo Metadata Strip */}
      <div className="cyber-card rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h2 className="text-xl font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
              <Shield className="w-5 h-5 text-accent-emerald" />
              <span>{data.repo_name}</span>
            </h2>
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-medium bg-surface-elevated text-text-secondary border border-surface-border">
              {data.repo_url.startsWith('fixture://') ? 'Verified Fixture Scenario' : 'Public GitHub Repo'}
            </span>
            {data.repo_url.startsWith('http') && (
              <a
                href={data.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-text-secondary hover:text-accent-emerald transition-colors"
                title="Open GitHub Repository"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-text-secondary font-mono">
            <button
              onClick={copyCommit}
              className="flex items-center gap-1.5 hover:text-text-primary transition-colors cursor-pointer group"
              title="Click to copy full commit SHA"
            >
              <GitCommit className="w-3.5 h-3.5 text-text-secondary" />
              <span>Commit: <code className="text-text-primary font-bold">{data.commit_sha.slice(0, 8)}</code></span>
              {copiedCommit ? (
                <Check className="w-3 h-3 text-severity-low" />
              ) : (
                <Copy className="w-3 h-3 opacity-60 group-hover:opacity-100" />
              )}
            </button>
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-text-secondary" /> Analyzed: {data.analyzed_at}
            </span>
          </div>
        </div>

        {/* Action Button for Remediation */}
        {data.remediations.length > 0 && (
          <button
            onClick={() => onSelectTab('remediation')}
            className="flex items-center space-x-2 px-4 py-2 rounded-md bg-accent-emerald hover:bg-accent-emerald-hover text-white text-xs font-semibold uppercase tracking-wider font-mono transition-colors cursor-pointer group"
          >
            <Sparkles className="w-4 h-4 text-white group-hover:rotate-12 transition-transform" />
            <span>Review {data.remediations.length} Safe Fix{data.remediations.length > 1 ? 'es' : ''}</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        )}
      </div>

      {/* Main Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Risk Score Card */}
        <div
          onClick={() => onSelectTab('risk')}
          className="enterprise-card p-5 relative overflow-hidden transition-colors cursor-pointer group"
        >
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
          <p className="text-[11px] text-text-secondary mt-2.5 line-clamp-2 font-mono">
            Deterministic formula factoring CVSS, CISA KEV weaponization, and reachability.
          </p>
        </div>

        {/* Components & SBOM */}
        <div
          onClick={() => onSelectTab('sbom')}
          className="enterprise-card p-5 transition-colors cursor-pointer group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-text-secondary">SBOM Inventory</span>
            <Cpu className="w-4 h-4 text-text-secondary group-hover:text-accent-emerald transition-colors" />
          </div>
          <div className="text-4xl font-black font-mono text-text-primary my-2">
            {data.total_components}
          </div>
          <div className="flex items-center space-x-2 mt-3 text-[11px] font-mono text-text-secondary">
            <span className="text-text-primary font-semibold">{directCount} Direct</span>
            <span>•</span>
            <span className="text-text-secondary font-semibold">{transitiveCount} Transitive</span>
          </div>
        </div>

        {/* Vulnerabilities Breakdown */}
        <div
          onClick={() => onSelectTab('vulnerabilities')}
          className="enterprise-card p-5 transition-colors cursor-pointer group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-text-secondary">Total Vulnerabilities</span>
            <Bug className="w-4 h-4 text-severity-critical group-hover:scale-105 transition-transform" />
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
          className="enterprise-card p-5 transition-colors cursor-pointer group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-text-secondary">Leaked Secrets</span>
            <KeyRound className="w-4 h-4 text-accent-amber group-hover:scale-105 transition-transform" />
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

      {/* Critical Attention Box & Explainable Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Urgent Findings */}
        <div className="lg:col-span-2 enterprise-card p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-surface-elevated">
            <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-severity-critical" />
              Critical Security Findings Requiring Action
            </h3>
            <span className="text-xs text-text-secondary font-mono">
              {data.vulnerabilities.filter(v => v.cisa_kev || v.severity === 'CRITICAL').length} High Priority
            </span>
          </div>

          <div className="space-y-3">
            {data.vulnerabilities.filter(v => v.cisa_kev || v.severity === 'CRITICAL').slice(0, 4).map((vuln) => (
              <div
                key={vuln.id}
                className="p-3.5 rounded-md bg-background-secondary border border-surface-border hover:border-surface-border/80 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-bold text-text-primary text-xs">{vuln.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-severity-critical/20 text-severity-critical border border-severity-critical/30">
                      {vuln.severity}
                    </span>
                    {vuln.cisa_kev && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-severity-critical text-white shadow-sm flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping"></span>
                        CISA KEV WEAPONIZED
                      </span>
                    )}
                    {vuln.reachability === 'reachable' && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-elevated text-text-secondary border border-surface-border">
                        Direct Application
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-secondary line-clamp-1">{vuln.explanation}</p>
                  <p className="text-[11px] font-mono text-text-secondary">
                    Package: <span className="font-bold text-text-primary">{vuln.package}</span> ({vuln.affected_version}) → Fix: <span className="text-severity-low font-bold">{vuln.fixed_version || 'Investigation required'}</span>
                  </p>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={() => onSelectTab('vulnerabilities')}
                    className="px-3 py-1.5 rounded-md bg-surface border border-surface-border text-text-primary text-xs font-mono hover:bg-surface-elevated transition-colors cursor-pointer"
                  >
                    Details
                  </button>
                  {vuln.fixed_version && (
                    <button
                      onClick={() => onSelectTab('remediation')}
                      className="px-3 py-1.5 rounded-md bg-accent-emerald/15 border border-accent-emerald/30 text-accent-emerald text-xs font-mono hover:bg-accent-emerald/25 transition-colors cursor-pointer flex items-center gap-1"
                    >
                      <span>Fix</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  )}
                </div>
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
        <div className="enterprise-card p-6 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary">
                Explainable Risk Formula
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-surface-elevated text-text-secondary border border-surface-border">
                Deterministic
              </span>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              {risk_overview.summary_explanation}
            </p>

            {/* Visual Factor Bars */}
            <div className="space-y-3 font-mono text-xs">
              <div>
                <div className="flex justify-between items-center text-text-secondary mb-1">
                  <span>CVSS Base Impact:</span>
                  <span className="text-text-primary font-bold">{data.risk_overview.breakdown.max_vulnerability_score?.toFixed(1) || '0.0'} / 35</span>
                </div>
                <div className="w-full bg-surface-elevated rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-accent-emerald h-full rounded-full"
                    style={{ width: `${Math.min(100, ((data.risk_overview.breakdown.max_vulnerability_score || 0) / 35) * 100)}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center text-text-secondary mb-1">
                  <span>CISA KEV Weaponized:</span>
                  <span className={data.risk_overview.breakdown.cisa_kev_active ? 'text-severity-critical font-bold' : 'text-text-secondary'}>
                    {data.risk_overview.breakdown.cisa_kev_active ? '+25 (Active Override)' : 'None (0)'}
                  </span>
                </div>
                <div className="w-full bg-surface-elevated rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${data.risk_overview.breakdown.cisa_kev_active ? 'bg-severity-critical w-full' : 'bg-transparent w-0'}`}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center text-text-secondary mb-1">
                  <span>Secrets Leaks Penalty:</span>
                  <span className="text-text-primary font-bold">+{data.risk_overview.breakdown.secret_risk_penalty?.toFixed(1) || '0.0'}</span>
                </div>
                <div className="w-full bg-surface-elevated rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-severity-high h-full rounded-full"
                    style={{ width: `${Math.min(100, ((data.risk_overview.breakdown.secret_risk_penalty || 0) / 25) * 100)}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center text-text-secondary mb-1">
                  <span>Suspicious Package Penalty:</span>
                  <span className="text-text-primary font-bold">+{data.risk_overview.breakdown.suspicious_dependency_penalty?.toFixed(1) || '0.0'}</span>
                </div>
                <div className="w-full bg-surface-elevated rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-accent-amber h-full rounded-full"
                    style={{ width: `${Math.min(100, ((data.risk_overview.breakdown.suspicious_dependency_penalty || 0) / 25) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-elevated flex items-center justify-between">
            <span className="text-xs text-text-secondary font-mono">Calibration Level:</span>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-severity-low/20 text-severity-low border border-severity-low/40 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> Authoritative (High)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
