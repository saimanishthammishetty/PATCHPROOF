import React, { useState } from 'react';
import type { RemediationProposal, DraftPRResponse } from '../types';
import {
  X, GitPullRequest, Lock, AlertTriangle, CheckCircle,
  ExternalLink, Loader2, ShieldCheck, Terminal, FileCode, Check
} from 'lucide-react';
import { submitDraftPR } from '../services/api';

interface DraftPRModalProps {
  analysisId: string;
  repoUrl: string;
  proposal: RemediationProposal;
  onClose: () => void;
  onSuccess: () => void;
}

export const DraftPRModal: React.FC<DraftPRModalProps> = ({
  analysisId,
  repoUrl,
  proposal,
  onClose,
  onSuccess
}) => {
  const [baseBranch, setBaseBranch] = useState('main');
  const [proposedBranch, setProposedBranch] = useState(
    `patchproof/fix-${proposal.package}-${proposal.proposed_version}`
  );
  const [prTitle, setPrTitle] = useState(
    `Upgrade ${proposal.package} to ${proposal.proposed_version} (Remediates ${proposal.advisories_resolved.join(', ')})`
  );
  const [userConfirmed, setUserConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prResult, setPrResult] = useState<DraftPRResponse | null>(null);

  const handleSubmit = async () => {
    if (!userConfirmed) {
      setError('Explicit user authorization checkbox is mandatory.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const res = await submitDraftPR({
        analysis_id: analysisId,
        remediation_id: proposal.id,
        base_branch: baseBranch,
        proposed_branch: proposedBranch,
        pr_title: prTitle,
        pr_body: `Automated remediation proposal for ${proposal.package}`,
        user_confirmed: true
      });
      setPrResult(res);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to submit draft pull request');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/85 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-surface border border-surface-border rounded-lg w-full max-w-2xl overflow-hidden font-mono text-xs my-8">
        {/* Modal Header */}
        <div className="p-5 border-b border-surface-border flex items-center justify-between bg-surface-elevated/40">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-md bg-surface-elevated border border-surface-border flex items-center justify-center">
              <GitPullRequest className="w-4 h-4 text-accent-emerald" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-text-primary">Draft Pull Request Review</h3>
              <p className="text-[11px] text-text-secondary">Human-in-the-loop remediation proposal</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary p-1.5 rounded-xl hover:bg-surface-elevated transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-5">
          {prResult ? (
            /* Success View */
            <div className="space-y-4 py-4 text-center">
              <div className="w-14 h-14 rounded-full bg-severity-low/20 border border-severity-low/40 flex items-center justify-center mx-auto text-severity-low">
                <CheckCircle className="w-7 h-7" />
              </div>
              <h4 className="text-base font-bold text-text-primary">Draft Pull Request Created</h4>
              <p className="text-text-secondary text-xs max-w-md mx-auto leading-relaxed font-sans">
                {prResult.message}
              </p>

              <div className="p-4 rounded-xl bg-background-secondary border border-surface-elevated text-left space-y-2.5 max-w-md mx-auto">
                <div className="flex justify-between items-center">
                  <span className="text-text-secondary">Draft PR Status:</span>
                  <span className="text-accent-emerald font-semibold">{prResult.draft_status}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text-secondary">Proposed Branch:</span>
                  <code className="text-text-primary font-bold">{prResult.branch_name}</code>
                </div>
                {prResult.pr_url && (
                  <div className="pt-2 border-t border-surface-elevated flex justify-between items-center">
                    <span className="text-text-secondary">GitHub Link:</span>
                    <a
                      href={prResult.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-emerald font-semibold hover:underline flex items-center gap-1.5 px-3 py-1 rounded-md bg-surface border border-surface-border"
                    >
                      <span>View on GitHub</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>

              {/* Safety Notice */}
              <div className="p-3.5 bg-severity-critical/10 border border-severity-critical/30 rounded-xl max-w-md mx-auto text-[11px] text-text-secondary text-left flex items-start gap-2.5">
                <Lock className="w-4 h-4 text-severity-critical shrink-0 mt-0.5" />
                <span className="leading-relaxed font-mono">{prResult.safety_notice}</span>
              </div>

              <div className="pt-3">
                <button
                  onClick={onClose}
                  className="px-6 py-2.5 rounded-xl bg-surface-elevated hover:bg-surface border border-surface-elevated text-text-primary font-bold cursor-pointer"
                >
                  Close Window
                </button>
              </div>
            </div>
          ) : (
            /* Review & Form View */
            <>
              {error && (
                <div className="p-3.5 bg-severity-critical/15 border border-severity-critical/40 rounded-xl text-severity-critical flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Strict Safety Guarantee Box */}
              <div className="p-4 bg-severity-critical/10 border border-severity-critical/30 rounded-xl flex items-start gap-3">
                <Lock className="w-5 h-5 text-severity-critical shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="font-bold text-severity-critical uppercase tracking-wider text-[11px]">
                    Architectural Safety Guarantee (NEVER_MERGE):
                  </span>
                  <p className="text-[11px] text-text-secondary leading-relaxed font-sans">
                    PATCHPROOF strictly opens PRs in <strong className="text-text-primary font-mono">DRAFT</strong> mode.
                    Automated merging is permanently disabled in the backend. Human code review, test validation, and manual merge are strictly required.
                  </p>
                </div>
              </div>

              {/* Form Inputs */}
              <div className="space-y-3.5">
                <div>
                  <label className="block text-text-secondary mb-1">Target Repository:</label>
                  <input
                    type="text"
                    disabled
                    value={repoUrl}
                    className="w-full bg-background-secondary border border-surface-elevated rounded-xl px-3.5 py-2 text-text-secondary font-mono select-none"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-text-secondary mb-1">Base Branch:</label>
                    <input
                      type="text"
                      value={baseBranch}
                      onChange={(e) => setBaseBranch(e.target.value)}
                      className="w-full bg-background-secondary border border-surface-border rounded-md px-3.5 py-2 text-text-primary focus:outline-none focus:border-accent-emerald font-mono transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-text-secondary mb-1">Proposed Branch:</label>
                    <input
                      type="text"
                      value={proposedBranch}
                      onChange={(e) => setProposedBranch(e.target.value)}
                      className="w-full bg-background-secondary border border-surface-border rounded-md px-3.5 py-2 text-text-primary focus:outline-none focus:border-accent-emerald font-mono transition-colors"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-text-secondary mb-1">Draft PR Title:</label>
                  <input
                    type="text"
                    value={prTitle}
                    onChange={(e) => setPrTitle(e.target.value)}
                    className="w-full bg-background-secondary border border-surface-border rounded-md px-3.5 py-2 text-text-primary focus:outline-none focus:border-accent-emerald font-mono transition-colors"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-text-secondary flex items-center gap-1.5">
                      <FileCode className="w-3.5 h-3.5 text-text-secondary" />
                      <span>Proposed Manifest Diff Preview:</span>
                    </label>
                    <span className="text-[10px] text-text-secondary/60">{proposal.manifest_path}</span>
                  </div>
                  <div className="p-3 bg-background-secondary border border-surface-border rounded-md max-h-36 overflow-x-auto font-mono text-[11px]">
                    <pre className="leading-relaxed">
                      {proposal.diff.split('\n').map((line, idx) => {
                        let color = 'text-text-secondary';
                        if (line.startsWith('+') && !line.startsWith('+++')) color = 'text-severity-low font-bold';
                        else if (line.startsWith('-') && !line.startsWith('---')) color = 'text-severity-critical font-bold';
                        else if (line.startsWith('@')) color = 'text-accent-amber';
                        return <div key={idx} className={color}>{line}</div>;
                      })}
                    </pre>
                  </div>
                </div>

                {/* Explicit Authorization Checkbox */}
                <div className="pt-1">
                  <label className="flex items-start space-x-3 p-3.5 rounded-md bg-surface-elevated/70 border border-surface-border cursor-pointer hover:border-surface-border/80 transition-colors">
                    <input
                      type="checkbox"
                      checked={userConfirmed}
                      onChange={(e) => setUserConfirmed(e.target.checked)}
                      className="mt-0.5 rounded border-surface-border text-accent-emerald focus:ring-0 cursor-pointer w-4 h-4"
                    />
                    <span className="text-text-primary leading-relaxed text-[11px] font-sans">
                      <strong className="font-mono text-accent-emerald">Explicit Authorization:</strong> I have reviewed the proposed dependency modification ({proposal.package} {proposal.current_version} → {proposal.proposed_version}) and authorize PATCHPROOF to open a <strong>DRAFT</strong> pull request.
                    </span>
                  </label>
                </div>
              </div>

              {/* Footer Actions */}
              <div className="pt-4 border-t border-surface-border flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-md bg-surface-elevated hover:bg-surface border border-surface-border text-text-secondary font-medium cursor-pointer transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={submitting || !userConfirmed}
                  className="flex items-center space-x-2 px-4 py-2 rounded-md bg-accent-emerald hover:bg-accent-emerald-hover text-white font-semibold uppercase tracking-wider disabled:opacity-40 transition-colors cursor-pointer"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Creating Draft PR...</span>
                    </>
                  ) : (
                    <>
                      <GitPullRequest className="w-4 h-4" />
                      <span>Submit DRAFT Pull Request</span>
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
