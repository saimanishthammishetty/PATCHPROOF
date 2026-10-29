import React from 'react';
import type { AnalysisResult } from '../types';
import { ShieldCheck, Cpu, Sliders, AlertOctagon, HelpCircle, Check, Info } from 'lucide-react';

interface RiskEngineTabProps {
  data: AnalysisResult;
}

export const RiskEngineTab: React.FC<RiskEngineTabProps> = ({ data }) => {
  const { risk_overview, health_findings } = data;

  return (
    <div className="space-y-6">
      {/* Risk Engine Header */}
      <div className="bg-surface border border-surface-elevated rounded-2xl p-5 shadow-xl">
        <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
          <Sliders className="w-5 h-5 text-brand-violet" />
          Transparent Risk & Confidence Engine
        </h2>
        <p className="text-xs text-text-secondary mt-1">
          Explainable, deterministic evaluation function (0 - 100). No black-box LLM risk hallucinations.
        </p>
      </div>

      {/* Mathematical Breakdown Model */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Formula Card */}
        <div className="bg-surface border border-surface-elevated rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary flex items-center gap-2">
            <Cpu className="w-4 h-4 text-brand-cyan" />
            Deterministic Scoring Function
          </h3>

          <div className="bg-background-secondary p-4 rounded-xl border border-surface-elevated font-mono text-xs text-text-primary space-y-2">
            <p className="text-brand-cyan font-bold">
              Finding Risk = (CVSS × 3.5) + (KEV × 25) + (EPSS × 20) + (Reachability × 10)
            </p>
            <p className="text-text-secondary text-[11px] leading-relaxed">
              Where CISA KEV membership acts as an immediate critical override ensuring a baseline score ≥ 80.
            </p>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="flex justify-between items-center py-2 border-b border-surface-elevated">
              <span className="text-text-secondary">0 – 19 Risk Points:</span>
              <span className="text-severity-low font-bold">Low Severity</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-surface-elevated">
              <span className="text-text-secondary">20 – 39 Risk Points:</span>
              <span className="text-severity-medium font-bold">Medium Severity</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-surface-elevated">
              <span className="text-text-secondary">40 – 69 Risk Points:</span>
              <span className="text-severity-high font-bold">High Severity</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-surface-elevated">
              <span className="text-text-secondary">70 – 100 Risk Points:</span>
              <span className="text-severity-critical font-bold">Critical Severity (Action Mandatory)</span>
            </div>
          </div>
        </div>

        {/* Confidence Model */}
        <div className="bg-surface border border-surface-elevated rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-brand-violet" />
            Confidence & Calibration Criteria
          </h3>

          <p className="text-xs text-text-secondary leading-relaxed">
            Confidence estimates how strongly available evidence supports the finding and proposed upgrade.
          </p>

          <div className="space-y-2.5 font-mono text-xs">
            <div className="p-3 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
              <span className="text-brand-cyan font-bold">HIGH Confidence:</span>
              <p className="text-text-secondary text-[11px]">
                Exact package identity corroborated by lockfile, authoritative advisory range, and verified upstream release.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
              <span className="text-severity-medium font-bold">MEDIUM Confidence:</span>
              <p className="text-text-secondary text-[11px]">
                Declared manifest version with advisory match, but no verified lockfile pin or test execution available.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
              <span className="text-text-secondary font-bold">LOW Confidence:</span>
              <p className="text-text-secondary text-[11px]">
                Heuristic warning only, ambiguous package name similarity, or unconfirmed affected range.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Suspicious Package & Dependency Health Feed */}
      <div className="bg-surface border border-surface-elevated rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-mono uppercase tracking-wider font-bold text-text-primary flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-severity-high" />
          Suspicious Package & Supply-Chain Health Indicators
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {health_findings.map((hf) => (
            <div
              key={`${hf.ecosystem}-${hf.package}`}
              className="p-4 rounded-xl bg-surface-elevated/60 border border-surface-elevated space-y-2 font-mono text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-text-primary">{hf.package}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  hf.health_score >= 8 ? 'bg-severity-low/20 text-severity-low' : 'bg-severity-high/20 text-severity-high'
                }`}>
                  Health: {hf.health_score}/10
                </span>
              </div>

              {hf.is_suspicious ? (
                <div className="text-severity-critical text-[11px] space-y-1">
                  {hf.suspicious_reasons.map((r, i) => (
                    <div key={i}>⚠️ {r}</div>
                  ))}
                </div>
              ) : (
                <div className="text-text-secondary text-[11px]">
                  Maintenance status: {hf.maintenance_status} (license: {hf.signals.license || 'declared'})
                </div>
              )}
            </div>
          ))}

          {health_findings.length === 0 && (
            <div className="col-span-2 p-8 text-center text-text-secondary font-mono text-xs">
              No suspicious package or degraded health indicators identified.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
