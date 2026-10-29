import React, { useState } from 'react';
import type { RemediationProposal, DraftPRResponse } from '../types';
import { 
  X, GitPullRequest, Lock, AlertTriangle, CheckCircle, 
  ExternalLink, Loader2, ShieldCheck, Terminal
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
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-surface border border-surface-elevated rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden font-mono text-xs my-8">
        {/* Modal Header */}
        <div className="p-5 border-b border-surface-elevated flex items-center justify-between bg-surface-elevated/40">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-violet/20 border border-brand-violet/40 flex items-center justify-center">
              <GitPullRequest className="w-4 h-4 text-brand-violet" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-text-primary">Draft Pull Request Review</h3>
              <p className="text-[11px] text-text-secondary">Safe, human-in-the-loop remediation proposal</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary p-1 rounded-lg hover:bg-surface-elevated transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-5">
          {prResult ? (
            /* Success View */
            <div className="space-y-4 py-4 text-center">
              <div className="w-12 h-12 rounded-full bg-severity-low/20 border border-severity-low/40 flex items-center justify-center mx-auto text-severity-low">
                <CheckCircle className="w-6 h-6" />
              </div>
              <h4 className="text-base font-bold text-text-primary">Draft Pull Request Successfully Created</h4>
              <p className="text-text-secondary text-xs max-w-md mx-auto leading-relaxed">
                {prResult.message}
              </p>

              <div className="p-4 rounded-xl bg-background-secondary border border-surface-elevated text-left space-y-2 max-w-md mx-auto">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Draft PR Status:</span>
                  <span className="text-brand-cyan font-bold">DRAFT (Peer Review Required)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Proposed Branch:</span>
                  <span className="text-text-primary font-bold">{prResult.branch_name}</span>
                </div>
                {prResult.pr_url && (
                  <div className="pt-2 border-t border-surface-elevated flex justify-between items-center">
                    <span className="text-text-secondary">Pull Request URL:</span>
                    <a
                      href={prResult.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-brand-violet font-bold hover:underline flex items-center gap-1"
                    >
                      <span>View on GitHub</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>

              {/* Safety Notice */}
              <div className="p-3 bg-brand-violet/10 border border-brand-violet/30 rounded-xl max-w-md mx-auto text-[11px] text-text-secondary text-left flex items-start gap-2">
                <Lock className="w-4 h-4 text-brand-cyan shrink-0 mt-0.5" />
                <span>{prResult.safety_notice}</span>
              </div>

              <div className="pt-4">
                <button
                  onClick={onClose}
                  className="px-6 py-2.5 rounded-xl bg-surface-elevated hover:bg-surface border border-surface-elevated text-text-primary font-bold"
                >
                  Close Window
                </button>
              </div>
            </div>
          ) : (
            /* Review & Form View */
            <>
              {error && (
                <div className="p-3 bg-severity-critical/15 border border-severity-critical/40 rounded-xl text-severity-critical flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Strict Safety Guarantee Box */}
              <div className="p-3.5 bg-severity-critical/10 border border-severity-critical/30 rounded-xl flex items-start gap-2.5">
                <Lock className="w-4 h-4 text-severity-critical shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <span className="font-bold text-severity-critical">Non-Negotiable Safety Guarantee:</span>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    PATCHPROOF strictly opens PRs in <strong className="text-text-primary">DRAFT</strong> mode.
                    Auto-merging is permanently disabled in the architecture. Human review and manual merge are strictly required.
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
                    className="w-full bg-background-secondary border border-surface-elevated rounded-lg px-3 py-2 text-text-secondary font-mono select-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-text-secondary mb-1">Base Branch:</label>
                    <input
                      type="text"
                      value={baseBranch}
                      onChange={(e) => setBaseBranch(e.target.value)}
                      className="w-full bg-surface-elevated border border-surface-elevated rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-brand-violet/50"
                    />
                  </div>
                  <div>
                    <label className="block text-text-secondary mb-1">Proposed Branch:</label>
                    <input
                      type="text"
                      value={proposedBranch}
                      onChange={(e) => setProposedBranch(e.target.value)}
                      className="w-full bg-surface-elevated border border-surface-elevated rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-brand-violet/50"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-text-secondary mb-1">Draft PR Title:</label>
                  <input
                    type="text"
                    value={prTitle}
                    onChange={(e) => setPrTitle(e.target.value)}
                    className="w-full bg-surface-elevated border border-surface-elevated rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-brand-violet/50"
                  />
                </div>

                <div>
                  <label className="block text-text-secondary mb-1">Proposed Manifest Diff Preview:</label>
                  <div className="p-3 bg-background-secondary border border-surface-elevated rounded-lg max-h-32 overflow-x-auto">
                    <pre className="text-[11px] leading-tight text-text-secondary">
                      {proposal.diff}
                    </pre>
                  </div>
                </div>

                {/* Explicit Authorization Checkbox */}
                <div className="pt-2">
                  <label className="flex items-start space-x-2.5 p-3 rounded-xl bg-surface-elevated/70 border border-surface-elevated cursor-pointer hover:border-brand-cyan/40 transition-colors">
                    <input
                      type="checkbox"
                      checked={userConfirmed}
                      onChange={(e) => setUserConfirmed(e.target.checked)}
                      className="mt-0.5 rounded border-surface-elevated text-brand-violet focus:ring-0"
                    />
                    <span className="text-text-primary leading-relaxed text-[11px]">
                      <strong>Explicit Authorization:</strong> I have reviewed the proposed dependency modification ({proposal.package} {proposal.current_version} → {proposal.proposed_version}) and authorize PATCHPROOF to open a <strong>DRAFT</strong> pull request.
                    </span>
                  </label>
                </div>
              </div>

              {/* Footer Actions */}
              <div className="pt-3 border-t border-surface-elevated flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl bg-surface-elevated hover:bg-surface border border-surface-elevated text-text-secondary font-bold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={submitting || !userConfirmed}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-violet to-brand-cyan text-white font-bold uppercase tracking-wider shadow-lg shadow-brand-violet/25 hover:opacity-95 disabled:opacity-40 transition-all"
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
