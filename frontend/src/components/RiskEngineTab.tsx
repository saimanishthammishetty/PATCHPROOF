import React from 'react';
import type { AnalysisResult } from '../types';
import { ShieldCheck, Cpu, Sliders, AlertOctagon, HelpCircle, Check, Info, Activity } from 'lucide-react';

interface RiskEngineTabProps {
  data: AnalysisResult;
}

export const RiskEngineTab: React.FC<RiskEngineTabProps> = ({ data }) => {
  const { risk_overview, health_findings } = data;

  return (
    <div className="space-y-6">
      {/* Risk Engine Header */}
      <div className="enterprise-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <Sliders className="w-5 h-5 text-accent-emerald" />
            Transparent Risk & Confidence Engine
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Explainable, deterministic evaluation function (0 - 100). No black-box LLM risk hallucinations.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1.5 rounded-md bg-surface-elevated text-text-secondary border border-surface-border font-medium flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-accent-emerald" />
            <span>Target Repo Score: {risk_overview.score}/100 ({risk_overview.label})</span>
          </span>
        </div>
      </div>

      {/* Mathematical Breakdown Model */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Formula Card */}
        <div className="enterprise-card p-6 space-y-4">
          <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary flex items-center gap-2">
            <Cpu className="w-4 h-4 text-accent-emerald" />
            Deterministic Scoring Function
          </h3>

          <div className="bg-background-secondary p-4 rounded-xl border border-surface-elevated font-mono text-xs text-text-primary space-y-2">
            <p className="text-accent-emerald font-semibold">
              Finding Risk = (CVSS × 3.5) + (KEV × 25) + (EPSS × 20) + (Reachability × 10)
            </p>
            <p className="text-text-secondary text-[11px] leading-relaxed">
              Where CISA KEV membership acts as an immediate critical override ensuring a baseline score ≥ 80.
            </p>
          </div>

          {/* Current Calculation Breakdown */}
          <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border font-mono text-xs space-y-1.5">
            <span className="text-[10px] text-text-secondary font-semibold uppercase tracking-wider">Computed for this Target Repository:</span>
            <div className="text-text-primary text-[11px] leading-relaxed">
              CVSS Base ({data.risk_overview.breakdown.max_vulnerability_score?.toFixed(1) || 0})
              + KEV Override ({data.risk_overview.breakdown.cisa_kev_active ? '25.0' : '0.0'})
              + Secret Penalty ({data.risk_overview.breakdown.secret_risk_penalty?.toFixed(1) || 0})
              + Suspicious Penalty ({data.risk_overview.breakdown.suspicious_dependency_penalty?.toFixed(1) || 0})
              = <strong className="text-accent-emerald font-bold">{risk_overview.score}/100</strong>
            </div>
          </div>

          <div className="space-y-2.5 font-mono text-xs pt-1">
            <div className="flex justify-between items-center py-1.5 border-b border-surface-elevated">
              <span className="text-text-secondary">0 – 19 Risk Points:</span>
              <span className="text-severity-low font-bold">Low Severity</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-surface-elevated">
              <span className="text-text-secondary">20 – 39 Risk Points:</span>
              <span className="text-severity-medium font-bold">Medium Severity</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-surface-elevated">
              <span className="text-text-secondary">40 – 69 Risk Points:</span>
              <span className="text-severity-high font-bold">High Severity</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-surface-elevated">
              <span className="text-text-secondary">70 – 100 Risk Points:</span>
              <span className="text-severity-critical font-bold">Critical Severity (Action Mandatory)</span>
            </div>
          </div>
        </div>

        {/* Confidence Model */}
        <div className="enterprise-card p-6 space-y-4">
          <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-accent-emerald" />
            Confidence & Calibration Criteria
          </h3>

          <p className="text-xs text-text-secondary leading-relaxed">
            Confidence estimates how strongly available evidence supports the finding and proposed upgrade.
          </p>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border space-y-1">
              <span className="text-accent-emerald font-bold">HIGH Confidence (Authoritative):</span>
              <p className="text-text-secondary text-[11px] leading-relaxed">
                Exact package identity corroborated by lockfile, authoritative advisory range, and verified upstream release.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-surface-elevated/70 border border-severity-medium/30 space-y-1">
              <span className="text-severity-medium font-bold">MEDIUM Confidence (Verified Heuristic):</span>
              <p className="text-text-secondary text-[11px] leading-relaxed">
                Declared manifest version with advisory match, but no verified lockfile pin or test execution available.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
              <span className="text-text-secondary font-bold">LOW Confidence (Tentative):</span>
              <p className="text-text-secondary text-[11px] leading-relaxed">
                Heuristic warning only, ambiguous package name similarity, or unconfirmed affected range.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Suspicious Package & Dependency Health Feed */}
      <div className="enterprise-card p-6 space-y-4">
        <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-severity-high" />
          Suspicious Package & Supply-Chain Health Indicators
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {health_findings.map((hf) => (
            <div
              key={`${hf.ecosystem}-${hf.package}`}
              className="p-4 rounded-xl bg-surface-elevated/60 border border-surface-elevated space-y-2.5 font-mono text-xs"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-text-primary text-sm">{hf.package}</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-surface-elevated text-text-secondary uppercase">
                    {hf.ecosystem}
                  </span>
                </div>
                <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                  hf.health_score >= 8 ? 'bg-severity-low/20 text-severity-low border border-severity-low/30' : 'bg-severity-high/20 text-severity-high border border-severity-high/30'
                }`}>
                  Health: {hf.health_score}/10
                </span>
              </div>

              {/* Progress bar for health */}
              <div className="w-full bg-surface rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full ${hf.health_score >= 8 ? 'bg-severity-low' : 'bg-severity-high'}`}
                  style={{ width: `${(hf.health_score / 10) * 100}%` }}
                />
              </div>

              {hf.is_suspicious ? (
                <div className="text-severity-critical text-[11px] space-y-1 pt-1">
                  {hf.suspicious_reasons.map((r, i) => (
                    <div key={i} className="flex items-start gap-1.5">
                      <span>⚠️</span>
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-text-secondary text-[11px] pt-1">
                  Maintenance status: <span className="text-text-primary font-semibold">{hf.maintenance_status}</span> (license: {hf.signals.license || 'declared'})
                </div>
              )}
            </div>
          ))}

          {health_findings.length === 0 && (
            <div className="col-span-2 p-8 text-center text-text-secondary font-mono text-xs bg-surface-elevated/30 rounded-xl">
              No suspicious package or degraded health indicators identified. All dependencies meet minimum health thresholds.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
