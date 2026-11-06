import React, { useState } from 'react';
import type { RemediationProposal } from '../types';
import {
  Wrench, GitPullRequest, AlertTriangle, CheckCircle2,
  Terminal, ShieldCheck, ArrowRight, FileCode, Copy, Check, Lock, Sparkles
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
  const [copiedTestCmd, setCopiedTestCmd] = useState(false);
  const [copiedDiff, setCopiedDiff] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');

  const activeProposal = remediations.find(r => r.id === selectedProposalId) || remediations[0];

  const filteredRemediations = remediations.filter(r =>
    r.package.toLowerCase().includes(searchFilter.toLowerCase()) ||
    r.ecosystem.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const copyTestCommand = () => {
    if (activeProposal) {
      navigator.clipboard.writeText(activeProposal.recommended_test_command);
      setCopiedTestCmd(true);
      setTimeout(() => setCopiedTestCmd(false), 2000);
    }
  };

  const copyDiffContent = () => {
    if (activeProposal) {
      navigator.clipboard.writeText(activeProposal.diff);
      setCopiedDiff(true);
      setTimeout(() => setCopiedDiff(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="enterprise-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <Wrench className="w-5 h-5 text-accent-emerald" />
            Remediation Workspace & Verification Engine
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Safe, evidence-backed dependency upgrade recommendations with manifest diffs and compatibility checks.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1.5 rounded-md bg-accent-emerald/15 text-accent-emerald border border-accent-emerald/30 font-semibold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-accent-emerald" />
            <span>{remediations.length} Actionable Fix{remediations.length > 1 ? 'es' : ''} Ready</span>
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
            <div className="flex items-center justify-between px-1">
              <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-text-secondary">
                Candidate Upgrades ({filteredRemediations.length})
              </h3>
            </div>

            {remediations.length > 3 && (
              <input
                type="text"
                placeholder="Filter packages..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full bg-background-secondary border border-surface-border rounded-md px-3 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-emerald font-mono"
              />
            )}

            <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
              {filteredRemediations.map((prop) => {
                const isSelected = prop.id === activeProposal?.id;
                return (
                  <div
                    key={prop.id}
                    onClick={() => setSelectedProposalId(prop.id)}
                    className={`p-4 rounded-md border transition-colors cursor-pointer font-mono text-xs ${
                      isSelected
                        ? 'bg-surface-elevated border-accent-emerald text-text-primary'
                        : 'bg-surface border-surface-border hover:border-surface-border/80 hover:bg-surface-elevated/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-text-primary text-sm">{prop.package}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        prop.breaking_change_warning ? 'bg-severity-high/20 text-severity-high border border-severity-high/30' : 'bg-severity-low/20 text-severity-low border border-severity-low/30'
                      }`}>
                        {prop.breaking_change_warning ? 'Major Bump' : 'Safe Patch'}
                      </span>
                    </div>

                    <div className="text-text-secondary text-[11px] flex items-center justify-between pt-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-text-secondary/80">{prop.current_version}</span>
                        <ArrowRight className="w-3 h-3 text-text-secondary" />
                        <span className="text-severity-low font-bold">{prop.proposed_version}</span>
                      </div>
                      <span className="text-[10px] text-text-secondary/60 uppercase">
                        {prop.ecosystem}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Active Proposal Inspection Workspace */}
          {activeProposal && (
            <div className="lg:col-span-8 enterprise-card p-6 space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
                <div>
                  <div className="flex items-center space-x-2.5">
                    <h3 className="text-xl font-bold font-mono text-text-primary">{activeProposal.package}</h3>
                    <span className="px-2.5 py-0.5 rounded-md bg-surface-elevated text-text-secondary text-xs font-mono uppercase font-medium border border-surface-border">
                      {activeProposal.ecosystem}
                    </span>
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-surface-elevated text-text-primary border border-surface-border font-medium">
                      {activeProposal.confidence} Confidence
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary mt-1 font-mono">
                    {activeProposal.reason}
                  </p>
                </div>

                {/* Primary CTA: Open Draft PR Modal */}
                <button
                  onClick={() => onOpenDraftModal(activeProposal)}
                  className="flex items-center space-x-2 px-4 py-2 rounded-md bg-accent-emerald hover:bg-accent-emerald-hover text-white text-xs font-semibold uppercase tracking-wider font-mono transition-colors shrink-0 cursor-pointer group"
                >
                  <GitPullRequest className="w-4 h-4 group-hover:rotate-12 transition-transform" />
                  <span>Review & Create Draft PR</span>
                </button>
              </div>

              {/* Version Comparison Card */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
                <div className="p-4 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
                  <span className="text-text-secondary uppercase text-[10px] font-bold">Current Version</span>
                  <p className="text-text-primary font-bold text-base">{activeProposal.current_version}</p>
                </div>
                <div className="p-4 rounded-xl bg-surface-elevated/70 border border-surface-border space-y-1">
                  <span className="text-text-secondary uppercase text-[10px] font-bold">Proposed Fixed Version</span>
                  <p className="text-severity-low font-bold text-base">{activeProposal.proposed_version}</p>
                </div>
                <div className="p-4 rounded-xl bg-surface-elevated/70 border border-surface-elevated space-y-1">
                  <span className="text-text-secondary uppercase text-[10px] font-bold">Verification Status</span>
                  <p className="text-accent-emerald font-semibold">{activeProposal.verification_status}</p>
                </div>
              </div>

              {/* Resolved Advisories Chips */}
              {activeProposal.advisories_resolved.length > 0 && (
                <div className="space-y-1.5 font-mono text-xs">
                  <span className="text-text-secondary uppercase text-[10px] font-bold tracking-wider">
                    Security Advisories Resolved:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {activeProposal.advisories_resolved.map(adv => (
                      <span key={adv} className="px-2.5 py-1 rounded-md bg-severity-critical/15 text-severity-critical border border-severity-critical/30 font-bold text-[11px]">
                        {adv}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Breaking Changes & Compatibility */}
              <div className="space-y-2 font-mono text-xs">
                <span className="text-text-secondary uppercase text-[11px] font-bold tracking-wider">
                  Compatibility & Breaking Change Assessment:
                </span>
                <div className="p-4 rounded-xl bg-surface-elevated/60 border border-surface-elevated space-y-2">
                  {activeProposal.compatibility_concerns.map((c, i) => (
                    <div key={i} className="flex items-start gap-2 text-text-primary">
                      <span className="text-accent-amber font-bold">▸</span>
                      <span>{c}</span>
                    </div>
                  ))}
                  {activeProposal.breaking_change_warning && (
                    <div className="flex items-center gap-2 text-severity-high font-bold pt-1 border-t border-surface-elevated/80">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>Major version bump detected. Review upstream changelog and API signatures before merging.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Recommended Test Command */}
              <div className="space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary uppercase text-[11px] font-bold tracking-wider flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-text-secondary" /> Suggested Verification Test Command:
                  </span>
                  <button
                    onClick={copyTestCommand}
                    className="text-text-secondary hover:text-accent-emerald transition-colors flex items-center gap-1 text-[11px] cursor-pointer"
                  >
                    {copiedTestCmd ? (
                      <>
                        <Check className="w-3 h-3 text-severity-low" />
                        <span className="text-severity-low font-bold">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy Command</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border text-accent-emerald font-mono text-xs select-all">
                  <code>{activeProposal.recommended_test_command}</code>
                </div>
              </div>

              {/* Manifest Unified Diff Viewer */}
              <div className="space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary uppercase text-[11px] font-bold tracking-wider flex items-center gap-1.5">
                    <FileCode className="w-3.5 h-3.5 text-text-secondary" /> Manifest Unified Diff (<code className="text-text-primary">{activeProposal.manifest_path}</code>):
                  </span>
                  <button
                    onClick={copyDiffContent}
                    className="text-text-secondary hover:text-accent-emerald transition-colors flex items-center gap-1 text-[11px] cursor-pointer"
                  >
                    {copiedDiff ? (
                      <>
                        <Check className="w-3 h-3 text-severity-low" />
                        <span className="text-severity-low font-bold">Copied Diff</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy Unified Diff</span>
                      </>
                    )}
                  </button>
                </div>

                <div className="p-4 rounded-xl bg-background-secondary border border-surface-elevated overflow-x-auto max-h-64 font-mono text-xs">
                  <pre className="leading-relaxed">
                    {activeProposal.diff.split('\n').map((line, idx) => {
                      let color = 'text-text-secondary';
                      let bg = '';
                      if (line.startsWith('+') && !line.startsWith('+++')) {
                        color = 'text-severity-low font-bold';
                        bg = 'bg-severity-low/10 px-1 rounded block';
                      } else if (line.startsWith('-') && !line.startsWith('---')) {
                        color = 'text-severity-critical font-bold';
                        bg = 'bg-severity-critical/10 px-1 rounded block';
                      } else if (line.startsWith('@')) {
                        color = 'text-accent-amber font-semibold';
                        bg = 'bg-accent-amber/10 px-1 rounded block';
                      } else if (line.startsWith('---') || line.startsWith('+++')) {
                        color = 'text-text-secondary font-semibold';
                        bg = 'block';
                      } else {
                        bg = 'block text-text-secondary/80';
                      }
                      return (
                        <span key={idx} className={`${color} ${bg}`}>
                          {line}
                        </span>
                      );
                    })}
                  </pre>
                </div>
              </div>

              {/* Safety Architecture Note */}
              <div className="p-3 rounded-xl bg-surface-elevated/40 border border-surface-elevated flex items-center space-x-2 text-[11px] font-mono text-text-secondary">
                <Lock className="w-3.5 h-3.5 text-severity-critical shrink-0" />
                <span>
                  <strong>NEVER_MERGE Safety Guarantee:</strong> PATCHPROOF opens Draft Pull Requests exclusively. Human review and sign-off are required.
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
