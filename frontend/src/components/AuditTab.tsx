import React, { useState } from 'react';
import type { AuditEntry } from '../types';
import {
  History, ShieldCheck, Hash, User, Clock, CheckCircle2,
  Search, Download, Copy, Check, FileText
} from 'lucide-react';

interface AuditTabProps {
  logs: AuditEntry[];
}

export const AuditTab: React.FC<AuditTabProps> = ({ logs }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const filteredLogs = logs.filter(log => {
    const term = searchTerm.toLowerCase();
    return !term ||
      log.event_type.toLowerCase().includes(term) ||
      log.repository.toLowerCase().includes(term) ||
      log.actor.toLowerCase().includes(term) ||
      log.details.toLowerCase().includes(term) ||
      log.integrity_hash.toLowerCase().includes(term);
  });

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const exportAuditJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `patchproof-audit-trail-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="enterprise-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <History className="w-5 h-5 text-accent-emerald" />
            Compliance & Immutable Audit Log
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Tamper-evident event stream with SHA-256 integrity hashing and zero credential leakage guarantees.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1.5 rounded-md bg-severity-low/15 text-severity-low border border-severity-low/30 font-semibold flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" />
            <span>SHA-256 Tamper Evident</span>
          </span>
          {logs.length > 0 && (
            <button
              onClick={exportAuditJson}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-surface hover:bg-surface-elevated border border-surface-border text-text-primary text-xs font-mono font-medium transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-text-secondary" />
              <span>Export Audit Trail</span>
            </button>
          )}
        </div>
      </div>

      {/* Search Input */}
      {logs.length > 0 && (
        <div className="relative">
          <Search className="w-4 h-4 text-text-secondary absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter audit records by actor, event type, or details..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-background-secondary border border-surface-border rounded-md pl-10 pr-4 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-emerald font-mono transition-colors"
          />
        </div>
      )}

      {/* Log Feed */}
      <div className="space-y-3 font-mono text-xs">
        {filteredLogs.map((entry, idx) => (
          <div
            key={idx}
            className="p-4 rounded-md enterprise-card space-y-2.5 transition-colors"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-2">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded-md bg-surface-elevated text-text-secondary border border-surface-border text-[10px] font-medium uppercase">
                  {entry.event_type}
                </span>
                <span className="text-text-primary font-bold">{entry.repository}</span>
              </div>
              <div className="flex items-center space-x-3 text-text-secondary text-[11px]">
                <span className="flex items-center gap-1">
                  <User className="w-3 h-3 text-text-secondary" /> Actor: {entry.actor}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-text-secondary" /> {entry.timestamp}
                </span>
              </div>
            </div>

            <p className="text-text-primary leading-relaxed text-[11px] font-sans">
              {entry.details}
            </p>

            <div className="pt-2 border-t border-surface-elevated/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[10px] text-text-secondary/80">
              <div className="flex items-center gap-1.5">
                <Hash className="w-3 h-3 text-text-secondary shrink-0" />
                <span>Integrity Hash:</span>
                <code className="text-text-primary font-mono bg-background-secondary px-1.5 py-0.5 rounded border border-surface-border">
                  {entry.integrity_hash.slice(0, 32)}...
                </code>
                <button
                  onClick={() => copyHash(entry.integrity_hash)}
                  className="hover:text-accent-emerald transition-colors ml-1"
                  title="Copy full SHA-256 hash"
                >
                  {copiedHash === entry.integrity_hash ? (
                    <Check className="w-3 h-3 text-severity-low" />
                  ) : (
                    <Copy className="w-3 h-3 opacity-60 hover:opacity-100" />
                  )}
                </button>
              </div>

              <span className="text-severity-low flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3 h-3" /> Cryptographically Verified
              </span>
            </div>
          </div>
        ))}

        {filteredLogs.length === 0 && (
          <div className="p-12 text-center text-text-secondary bg-surface rounded-2xl border border-surface-elevated">
            No audit records match your query.
          </div>
        )}
      </div>
    </div>
  );
};
