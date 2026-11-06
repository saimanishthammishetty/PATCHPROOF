import React, { useState } from 'react';
import type { RemediationProposal, DraftPRResponse } from '../types';
import {
  X, GitPullRequest, Lock, AlertTriangle, CheckCircle,
  ExternalLink, Loader2, ShieldCheck, Terminal, FileCode, Check,
  GitBranch, GitCommit, FileText, Bug, ArrowRight
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
    `patchproof/fix-${proposal.package.replace(/[^a-zA-Z0-9._-]/g, '-')}-${proposal.proposed_version.replace(/[^a-zA-Z0-9._-]/g, '-')}`
  );
  const [prTitle, setPrTitle] = useState(
    `Security remediation — PATCHPROOF: Upgrade ${proposal.package} to ${proposal.proposed_version}`
  );
  const [userConfirmed, setUserConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prResult, setPrResult] = useState<DraftPRResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return; // Prevent duplicate submissions

    if (!userConfirmed) {
      setError('Explicit user authorization checkbox is mandatory before creating a draft PR.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const res = await submitDraftPR({
        analysis_id: analysisId,
        remediation_id: proposal.id,
        base_branch: baseBranch.trim() || 'main',
        proposed_branch: proposedBranch.trim() || undefined,
        pr_title: prTitle.trim(),
        pr_body: `Automated remediation proposal for ${proposal.package}`,
        user_confirmed: true
      });

      if (!res.success) {
        setError(res.message || 'GitHub API rejected pull request creation.');
      } else {
        setPrResult(res);
        onSuccess();
      }
    } catch (err: any) {
      let msg = err.message || 'Failed to submit draft pull request';
      if (err.response?.data?.detail) {
        msg = err.response.data.detail;
      }
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/85 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-surface border border-surface-border rounded-lg w-full max-w-2xl overflow-hidden font-mono text-xs my-8 shadow-2xl">
        {/* Modal Header */}
        <div className="p-5 border-b border-surface-border flex items-center justify-between bg-surface-elevated/40">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-md bg-accent-emerald/15 border border-accent-emerald/30 flex items-center justify-center">
              <GitPullRequest className="w-4 h-4 text-accent-emerald" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-text-primary">Create GitHub Draft PR</h3>
              <p className="text-[11px] text-text-secondary">Human-in-the-loop security remediation workflow</p>
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
            /* Success / Results View */
            <div className="space-y-4 py-2 text-center">
              <div className={`w-14 h-14 rounded-full flex items-center justify-center mx-auto ${
                prResult.verified_on_github
                  ? 'bg-accent-emerald/20 border border-accent-emerald/40 text-accent-emerald'
                  : 'bg-accent-amber/20 border border-accent-amber/40 text-accent-amber'
              }`}>
                {prResult.verified_on_github ? <CheckCircle className="w-7 h-7" /> : <GitPullRequest className="w-7 h-7" />}
              </div>

              <div>
                <h4 className="text-base font-bold text-text-primary">
                  {prResult.verified_on_github
                    ? `Live GitHub Draft PR #${prResult.pr_number || ''} Created`
                    : 'Draft Pull Request Preview Generated'}
                </h4>
                <p className="text-text-secondary text-xs max-w-lg mx-auto leading-relaxed font-sans mt-1">
                  {prResult.message}
                </p>
              </div>

              {/* Detailed Verified Metrics Grid */}
              <div className="p-4 rounded-xl bg-background-secondary border border-surface-border text-left space-y-2.5 max-w-lg mx-auto font-mono text-[11px]">
                <div className="flex justify-between items-center py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">Verification Status:</span>
                  <span className={`font-bold px-2 py-0.5 rounded ${
                    prResult.verified_on_github
                      ? 'bg-accent-emerald/15 text-accent-emerald border border-accent-emerald/30'
                      : 'bg-surface-elevated text-text-secondary'
                  }`}>
                    {prResult.draft_status}
                  </span>
                </div>

                {prResult.pr_number && (
                  <div className="flex justify-between items-center py-1 border-b border-surface-border/50">
                    <span className="text-text-secondary">Pull Request Number:</span>
                    <span className="text-text-primary font-bold">#{prResult.pr_number} (Draft)</span>
                  </div>
                )}

                <div className="flex justify-between items-center py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">Head (New Branch):</span>
                  <code className="text-accent-emerald font-bold">{prResult.branch_name}</code>
                </div>

                <div className="flex justify-between items-center py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">Base (Target Branch):</span>
                  <code className="text-text-primary">{prResult.base_branch || baseBranch}</code>
                </div>

                {prResult.commit_sha && (
                  <div className="flex justify-between items-center py-1 border-b border-surface-border/50">
                    <span className="text-text-secondary">Commit SHA:</span>
                    <code className="text-text-primary font-bold">{prResult.commit_sha.slice(0, 10)}...</code>
                  </div>
                )}

                <div className="flex justify-between items-start py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">Modified Files:</span>
                  <div className="text-right">
                    {(prResult.changed_files && prResult.changed_files.length > 0 ? prResult.changed_files : [proposal.manifest_path]).map((f) => (
                      <div key={f} className="text-text-primary font-bold">{f}</div>
                    ))}
                  </div>
                </div>

                {prResult.pr_url && (
                  <div className="pt-2 flex justify-between items-center">
                    <span className="text-text-secondary">GitHub Link:</span>
                    <a
                      href={prResult.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-emerald font-semibold hover:underline flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-surface border border-accent-emerald/40 hover:bg-surface-elevated transition-colors"
                    >
                      <span>View Pull Request on GitHub</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                )}
              </div>

              {/* Safety Guarantee Box */}
              <div className="p-3.5 bg-severity-critical/10 border border-severity-critical/30 rounded-xl max-w-lg mx-auto text-[11px] text-text-secondary text-left flex items-start gap-2.5">
                <Lock className="w-4 h-4 text-severity-critical shrink-0 mt-0.5" />
                <span className="leading-relaxed font-mono">{prResult.safety_notice}</span>
              </div>

              <div className="pt-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-6 py-2.5 rounded-xl bg-surface-elevated hover:bg-surface border border-surface-border text-text-primary font-bold cursor-pointer transition-colors"
                >
                  Close Window
                </button>
              </div>
            </div>
          ) : (
            /* Review & Form View */
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3.5 bg-severity-critical/15 border border-severity-critical/40 rounded-xl text-severity-critical flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <div className="leading-relaxed">{error}</div>
                </div>
              )}

              {/* Strict Safety Guarantee Box */}
              <div className="p-4 bg-severity-critical/10 border border-severity-critical/30 rounded-xl flex items-start gap-3">
                <Lock className="w-5 h-5 text-severity-critical shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="font-bold text-severity-critical uppercase tracking-wider text-[11px]">
                    Architectural Safety Guarantee (NEVER_MERGE Active):
                  </span>
                  <p className="text-[11px] text-text-secondary leading-relaxed font-sans">
                    PATCHPROOF strictly creates pull requests in <strong className="text-text-primary font-mono">DRAFT</strong> mode.
                    Automated merging is permanently disabled in the backend. Human code review, testing, and manual merge are strictly enforced.
                  </p>
                </div>
              </div>

              {/* Target & Scope Review */}
              <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border space-y-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-text-secondary">Target Repository:</span>
                    <div className="font-bold text-text-primary truncate">{repoUrl}</div>
                  </div>
                  <div>
                    <span className="text-text-secondary">File to be Modified:</span>
                    <div className="font-bold text-accent-emerald truncate">{proposal.manifest_path}</div>
                  </div>
                </div>

                <div className="pt-2 border-t border-surface-border/60 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                  <div className="flex items-center gap-2">
                    <span className="text-text-secondary">Proposed Upgrade:</span>
                    <span className="text-text-primary font-bold">{proposal.package}</span>
                    <span className="text-text-secondary">({proposal.current_version})</span>
                    <ArrowRight className="w-3 h-3 text-text-secondary" />
                    <span className="text-severity-low font-bold">{proposal.proposed_version}</span>
                  </div>

                  {proposal.advisories_resolved.length > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-text-secondary text-[10px]">Resolves:</span>
                      {proposal.advisories_resolved.slice(0, 3).map((adv) => (
                        <span key={adv} className="px-1.5 py-0.2 rounded bg-surface-elevated text-accent-emerald text-[10px] font-bold border border-surface-border">
                          {adv}
                        </span>
                      ))}
                      {proposal.advisories_resolved.length > 3 && (
                        <span className="text-[10px] text-text-secondary">+{proposal.advisories_resolved.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Form Inputs */}
              <div className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-text-secondary mb-1 flex items-center gap-1">
                      <GitBranch className="w-3 h-3 text-text-secondary" />
                      <span>Base Branch (Target):</span>
                    </label>
                    <input
                      type="text"
                      value={baseBranch}
                      onChange={(e) => setBaseBranch(e.target.value)}
                      placeholder="main"
                      className="w-full bg-background-secondary border border-surface-border rounded-md px-3.5 py-2 text-text-primary focus:outline-none focus:border-accent-emerald font-mono transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-text-secondary mb-1 flex items-center gap-1">
                      <GitBranch className="w-3 h-3 text-accent-emerald" />
                      <span>New Branch to Create:</span>
                    </label>
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

                {/* Diff Preview */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-text-secondary flex items-center gap-1.5">
                      <FileCode className="w-3.5 h-3.5 text-text-secondary" />
                      <span>Unified Manifest Diff to be Committed:</span>
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
                      <strong className="font-mono text-accent-emerald">Explicit Authorization:</strong> I have reviewed the proposed dependency upgrade ({proposal.package} {proposal.current_version} → {proposal.proposed_version}) and authorize PATCHPROOF to create a <strong>DRAFT</strong> pull request on GitHub.
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
                  type="submit"
                  disabled={submitting || !userConfirmed}
                  className="flex items-center space-x-2 px-4 py-2 rounded-md bg-accent-emerald hover:bg-accent-emerald-hover text-white font-semibold uppercase tracking-wider disabled:opacity-40 transition-colors cursor-pointer"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Creating Real Draft PR...</span>
                    </>
                  ) : (
                    <>
                      <GitPullRequest className="w-4 h-4" />
                      <span>Create GitHub Draft PR</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
