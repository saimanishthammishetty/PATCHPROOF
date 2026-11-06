import React, { useState } from 'react';
import type { SecretFinding } from '../types';
import {
  KeyRound, ShieldAlert, CheckCircle2, RotateCcw, AlertTriangle,
  GitCommit, FileText, Copy, Check, Lock, ShieldCheck
} from 'lucide-react';

interface SecretsTabProps {
  secrets: SecretFinding[];
}

export const SecretsTab: React.FC<SecretsTabProps> = ({ secrets }) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyToClipboard = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const uniqueFiles = new Set(secrets.map(s => s.file_path)).size;

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="enterprise-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-accent-amber" />
            Secret Scanner & Git-History Leak Detector
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Deterministic entropy & regex analysis across the latest tree and commit logs. Sensitive tokens are strictly redacted.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1.5 rounded-xl bg-severity-critical/15 text-severity-critical border border-severity-critical/30 font-bold flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            <span>Zero-Leak Redaction Active</span>
          </span>
        </div>
      </div>

      {/* KPI Counters */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
        <div className="p-4 rounded-xl bg-surface border border-surface-elevated flex items-center justify-between">
          <span className="text-text-secondary uppercase text-[11px]">Exposed Credentials</span>
          <span className={`text-2xl font-black ${secrets.length > 0 ? 'text-severity-critical' : 'text-severity-low'}`}>
            {secrets.length}
          </span>
        </div>
        <div className="p-4 rounded-xl bg-surface border border-surface-elevated flex items-center justify-between">
          <span className="text-text-secondary uppercase text-[11px]">Affected Files</span>
          <span className="text-2xl font-black text-text-primary">{uniqueFiles}</span>
        </div>
        <div className="p-4 rounded-xl bg-surface border border-surface-elevated flex items-center justify-between">
          <span className="text-text-secondary uppercase text-[11px]">Leak Redaction Status</span>
          <span className="text-xs font-bold text-severity-low flex items-center gap-1">
            <ShieldCheck className="w-4 h-4" /> 100% Masked in API
          </span>
        </div>
      </div>

      {/* Secret Findings List */}
      <div className="space-y-4">
        {secrets.map((secret, idx) => (
          <div
            key={idx}
            className="enterprise-card p-5 space-y-4"
          >
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-elevated pb-3">
              <div className="flex items-center space-x-2.5">
                <ShieldAlert className="w-4 h-4 text-severity-critical" />
                <span className="text-sm font-bold font-mono text-text-primary">{secret.secret_type}</span>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-severity-critical/20 text-severity-critical border border-severity-critical/40 uppercase">
                  Exposed Credential
                </span>
              </div>
              <div className="flex items-center space-x-3 text-xs font-mono text-text-secondary">
                <span className="flex items-center gap-1">
                  <GitCommit className="w-3.5 h-3.5 text-text-secondary" /> Commit: <code className="text-text-primary font-bold">{secret.commit_sha || 'HEAD'}</code>
                </span>
                {secret.line_number && (
                  <span className="px-1.5 py-0.5 rounded bg-surface-elevated text-text-primary">
                    Line: {secret.line_number}
                  </span>
                )}
              </div>
            </div>

            {/* Redacted Token Box */}
            <div className="bg-background-secondary p-4 rounded-xl border border-surface-elevated font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <span className="text-text-secondary uppercase text-[10px] font-bold tracking-wider">Redacted Token:</span>
                <span className="text-severity-critical font-bold bg-surface px-3 py-1 rounded-md border border-surface-border tracking-widest selection:bg-severity-critical/20">
                  {secret.masked_value}
                </span>
              </div>
              <div className="text-text-secondary text-[11px] flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-text-secondary" />
                <span className="text-text-primary font-semibold">{secret.file_path}</span>
                <button
                  onClick={() => copyToClipboard(`file-${idx}`, secret.file_path)}
                  className="text-text-secondary hover:text-accent-emerald transition-colors ml-1"
                  title="Copy file path"
                >
                  {copiedKey === `file-${idx}` ? (
                    <Check className="w-3 h-3 text-severity-low" />
                  ) : (
                    <Copy className="w-3 h-3 opacity-60 hover:opacity-100" />
                  )}
                </button>
              </div>
            </div>

            {/* Playbook Rotation Box */}
            <div className="bg-surface-elevated/70 p-4 rounded-xl border border-surface-elevated text-xs font-mono space-y-2">
              <span className="text-severity-high font-bold text-[11px] uppercase tracking-wider flex items-center gap-1.5">
                <RotateCcw className="w-3.5 h-3.5" /> Mandatory Revocation & Rotation Procedure:
              </span>
              <p className="text-text-primary leading-relaxed font-sans">
                {secret.remediation_instructions}
              </p>
            </div>
          </div>
        ))}

        {secrets.length === 0 && (
          <div className="p-16 text-center text-text-secondary font-mono bg-surface rounded-2xl border border-surface-elevated">
            <CheckCircle2 className="w-12 h-12 text-severity-low mx-auto mb-3 opacity-90" />
            <h3 className="text-base font-bold text-text-primary">No Credential Leaks Detected</h3>
            <p className="text-xs text-text-secondary mt-1 max-w-md mx-auto leading-relaxed">
              Static repository files and commit history are completely clean of high-entropy API tokens, private keys, and cloud credentials.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
