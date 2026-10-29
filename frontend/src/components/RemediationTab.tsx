import React, { useState } from 'react';
import type { RemediationProposal } from '../types';
import { 
  Wrench, GitPullRequest, AlertTriangle, CheckCircle2, 
  Terminal, ShieldCheck, ArrowRight, FileCode
} from 'lucide-react';

interface RemediationTabProps {
  remediations: RemediationProposal[];
  onOpenDraftModal: (proposal: RemediationProposal) => void;
}

export const RemediationTab: React.FC<RemediationTabProps> = ({ 
  remediations, 
  onOpenDraftModal 
}) => {
  const [selectedProposalId, setSelectedProposalId] = useState<string>(
    remediations.length > 0 ? remediations[0].id : ''
  );

  const activeProposal = remediations.find(r => r.id === selectedProposalId) || remediations[0];

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="bg-surface border border-surface-elevated rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <Wrench className="w-5 h-5 text-brand-cyan" />
            Remediation Workspace & Verification Engine
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Safe, evidence-backed dependency upgrade recommendations with manifest diffs and compatibility checks.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-full bg-brand-violet/20 text-brand-violet border border-brand-violet/40 font-bold">
            {remediations.length} Actionable Fix{remediations.length > 1 ? 'es' : ''} Prepared
          </span>
        </div>
      </div>

      {remediations.length === 0 ? (
        <div className="p-16 text-center text-text-secondary font-mono bg-surface rounded-2xl border border-surface-elevated">
          <ShieldCheck className="w-12 h-12 text-severity-low mx-auto mb-3 opacity-90" />
          <h3 className="text-base font-bold text-text-primary">No Remediations Required</h3>
          <p className="text-xs text-text-secondary mt-1">
            All detected dependencies are currently within secure version bounds or have no verified upgrade paths.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Proposal List Sidebar */}
          <div className="lg:col-span-4 space-y-3">
            <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-text-secondary px-1">
              Candidate Upgrades
            </h3>
            {remediations.map((prop) => {
              const isSelected = prop.id === activeProposal?.id;
              return (
                <div
                  key={prop.id}
                  onClick={() => setSelectedProposalId(prop.id)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer font-mono text-xs ${
                    isSelected
                      ? 'bg-surface-elevated border-brand-cyan/60 shadow-lg'
                      : 'bg-surface border-surface-elevated hover:border-brand-violet/40'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-text-primary text-sm">{prop.package}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      prop.breaking_change_warning ? 'bg-severity-high/20 text-severity-high' : 'bg-severity-low/20 text-severity-low'
                    }`}>
                      {prop.breaking_change_warning ? 'Major Bump' : 'Safe Patch'}
                    </span>
                  </div>
                  <div className="text-text-secondary text-[11px] flex items-center gap-1.5">
                    <span>{prop.current_version}</span>
                    <ArrowRight className="w-3 h-3 text-brand-cyan" />
                    <span className="text-severity-low font-bold">{prop.proposed_version}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Active Proposal Inspection Workspace */}
          {activeProposal && (
            <div className="lg:col-span-8 bg-surface border border-surface-elevated rounded-2xl p-6 shadow-xl space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-elevated pb-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="text-lg font-bold font-mono text-text-primary">{activeProposal.package}</h3>
                    <span className="px-2.5 py-0.5 rounded bg-surface-elevated text-brand-cyan text-xs font-mono uppercase font-semibold">
                      {activeProposal.ecosystem}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary mt-1 font-mono">
                    {activeProposal.reason}
                  </p>
                </div>

                {/* Primary CTA: Open Draft PR Modal */}
                <button
                  onClick={() => onOpenDraftModal(activeProposal)}
                  className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-brand-violet to-brand-cyan text-white text-xs font-bold uppercase tracking-wider font-mono shadow-lg shadow-brand-violet/25 hover:opacity-95 transition-all shrink-0"
                >
                  <GitPullRequest className="w-4 h-4" />
                  <span>Review & Create Draft PR</span>
                </button>
              </div>

              {/* Version Comparison Card */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
                <div className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
                  <span className="text-text-secondary uppercase text-[10px] font-bold">Current Version</span>
                  <p className="text-text-primary font-bold text-sm">{activeProposal.current_version}</p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
                  <span className="text-text-secondary uppercase text-[10px] font-bold">Proposed Fixed Version</span>
                  <p className="text-severity-low font-bold text-sm">{activeProposal.proposed_version}</p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
                  <span className="text-text-secondary uppercase text-[10px] font-bold">Verification Status</span>
                  <p className="text-brand-cyan font-bold">{activeProposal.verification_status}</p>
                </div>
              </div>

              {/* Breaking Changes & Compatibility */}
              <div className="space-y-2 font-mono text-xs">
                <span className="text-text-secondary uppercase text-[11px] font-bold tracking-wider">
                  Compatibility & Breaking Change Assessment:
                </span>
                <div className="p-3.5 rounded-xl bg-surface-elevated/60 border border-surface-elevated space-y-1.5">
                  {activeProposal.compatibility_concerns.map((c, i) => (
                    <div key={i} className="flex items-start gap-2 text-text-primary">
                      <span className="text-brand-cyan">▸</span>
                      <span>{c}</span>
                    </div>
                  ))}
                  {activeProposal.breaking_change_warning && (
                    <div className="flex items-center gap-2 text-severity-high font-bold pt-1">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>Major version bump detected. Review upstream changelog and API signatures.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Recommended Test Command */}
              <div className="space-y-2 font-mono text-xs">
                <span className="text-text-secondary uppercase text-[11px] font-bold tracking-wider flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-brand-cyan" /> Suggested Verification Test Command:
                </span>
                <div className="p-3 rounded-lg bg-background-secondary border border-surface-elevated text-brand-cyan font-bold">
                  {activeProposal.recommended_test_command}
                </div>
              </div>

              {/* Manifest Unified Diff Viewer */}
              <div className="space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary uppercase text-[11px] font-bold tracking-wider flex items-center gap-1.5">
                    <FileCode className="w-3.5 h-3.5 text-brand-violet" /> Manifest Unified Diff ({activeProposal.manifest_path}):
                  </span>
                </div>
                <div className="p-4 rounded-xl bg-background-secondary border border-surface-elevated overflow-x-auto max-h-56">
                  <pre className="text-xs leading-relaxed">
                    {activeProposal.diff.split('\n').map((line, idx) => {
                      let color = 'text-text-secondary';
                      if (line.startsWith('+') && !line.startsWith('+++')) color = 'text-severity-low font-bold bg-severity-low/10 px-1 rounded';
                      else if (line.startsWith('-') && !line.startsWith('---')) color = 'text-severity-critical font-bold bg-severity-critical/10 px-1 rounded';
                      else if (line.startsWith('@')) color = 'text-brand-violet font-semibold';
                      return (
                        <div key={idx} className={color}>
                          {line}
                        </div>
                      );
                    })}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
