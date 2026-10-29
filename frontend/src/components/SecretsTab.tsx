import React from 'react';
import type { SecretFinding } from '../types';
import { KeyRound, ShieldAlert, CheckCircle2, RotateCcw, AlertTriangle, GitCommit, FileText } from 'lucide-react';

interface SecretsTabProps {
  secrets: SecretFinding[];
}

export const SecretsTab: React.FC<SecretsTabProps> = ({ secrets }) => {
  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="bg-surface border border-surface-elevated rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-brand-cyan" />
            Secret Scanner & Git-History Leak Detector
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Deterministic entropy & regex analysis across latest tree and commit logs. Sensitive tokens are strictly redacted.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-full bg-severity-critical/15 text-severity-critical border border-severity-critical/30 font-bold">
            Zero-Leak Redaction Active
          </span>
        </div>
      </div>

      {/* Secret Findings List */}
      <div className="space-y-4">
        {secrets.map((secret, idx) => (
          <div
            key={idx}
            className="bg-surface border border-severity-critical/30 rounded-2xl p-5 shadow-lg space-y-4 transition-all hover:border-severity-critical/60"
          >
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-elevated pb-3">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 text-severity-critical" />
                <span className="text-sm font-bold font-mono text-text-primary">{secret.secret_type}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-severity-critical/20 text-severity-critical border border-severity-critical/40 uppercase">
                  Exposed Credential
                </span>
              </div>
              <div className="flex items-center space-x-3 text-xs font-mono text-text-secondary">
                <span className="flex items-center gap-1">
                  <GitCommit className="w-3.5 h-3.5 text-brand-cyan" /> Commit: {secret.commit_sha || 'HEAD'}
                </span>
                {secret.line_number && (
                  <span>Line: {secret.line_number}</span>
                )}
              </div>
            </div>

            {/* Redacted Token Box */}
            <div className="bg-background-secondary p-3.5 rounded-xl border border-surface-elevated font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-3">
                <span className="text-text-secondary uppercase text-[10px] font-bold tracking-wider">Redacted Token:</span>
                <span className="text-brand-cyan font-bold bg-surface px-2.5 py-1 rounded border border-surface-elevated tracking-widest">
                  {secret.masked_value}
                </span>
              </div>
              <div className="text-text-secondary text-[11px] flex items-center gap-1">
                <FileText className="w-3.5 h-3.5 text-text-secondary" /> {secret.file_path}
              </div>
            </div>

            {/* Playbook Rotation Box */}
            <div className="bg-surface-elevated/70 p-4 rounded-xl border border-surface-elevated text-xs font-mono space-y-1.5">
              <span className="text-severity-high font-bold text-[11px] uppercase tracking-wider flex items-center gap-1.5">
                <RotateCcw className="w-3.5 h-3.5" /> Required Revocation & Rotation Procedure:
              </span>
              <p className="text-text-primary leading-relaxed">
                {secret.remediation_instructions}
              </p>
            </div>
          </div>
        ))}

        {secrets.length === 0 && (
          <div className="p-12 text-center text-text-secondary font-mono bg-surface rounded-2xl border border-surface-elevated">
            <CheckCircle2 className="w-10 h-10 text-severity-low mx-auto mb-3 opacity-90" />
            <h3 className="text-sm font-bold text-text-primary">No Credential Leaks Detected</h3>
            <p className="text-xs text-text-secondary mt-1">
              Static files and commit history are clean of high-entropy API tokens, private keys, and cloud credentials.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
