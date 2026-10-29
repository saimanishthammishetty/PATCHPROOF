import React from 'react';
import type { AuditEntry } from '../types';
import { History, ShieldCheck, Hash, User, Clock, CheckCircle2 } from 'lucide-react';

interface AuditTabProps {
  logs: AuditEntry[];
}

export const AuditTab: React.FC<AuditTabProps> = ({ logs }) => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-surface border border-surface-elevated rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <History className="w-5 h-5 text-brand-violet" />
            Compliance & Immutable Audit Log
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Tamper-evident event stream with SHA-256 integrity hashing and zero credential leakage guarantees.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-full bg-severity-low/20 text-severity-low border border-severity-low/40 font-bold flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" /> SHA-256 Tamper Evident
          </span>
        </div>
      </div>

      {/* Log Feed */}
      <div className="space-y-3 font-mono text-xs">
        {logs.map((entry, idx) => (
          <div
            key={idx}
            className="p-4 rounded-xl bg-surface border border-surface-elevated space-y-2 hover:border-brand-violet/30 transition-colors shadow-md"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-elevated pb-2">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded bg-brand-violet/20 text-brand-violet border border-brand-violet/30 text-[10px] font-bold uppercase">
                  {entry.event_type}
                </span>
                <span className="text-text-primary font-bold">{entry.repository}</span>
              </div>
              <div className="flex items-center space-x-3 text-text-secondary text-[11px]">
                <span className="flex items-center gap-1">
                  <User className="w-3 h-3 text-brand-cyan" /> Actor: {entry.actor}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-text-secondary" /> {entry.timestamp}
                </span>
              </div>
            </div>

            <p className="text-text-primary leading-relaxed text-[11px]">
              {entry.details}
            </p>

            <div className="pt-2 flex items-center justify-between text-[10px] text-text-secondary/70">
              <span className="flex items-center gap-1">
                <Hash className="w-3 h-3 text-brand-cyan" /> Integrity Hash: <code className="text-brand-cyan/80">{entry.integrity_hash.slice(0, 32)}...</code>
              </span>
              <span className="text-severity-low flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Verified
              </span>
            </div>
          </div>
        ))}

        {logs.length === 0 && (
          <div className="p-12 text-center text-text-secondary bg-surface rounded-2xl border border-surface-elevated">
            No audit records registered yet.
          </div>
        )}
      </div>
    </div>
  );
};
