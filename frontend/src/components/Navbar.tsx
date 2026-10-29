import React from 'react';
import { Shield, Lock, Terminal, Activity, FileCheck2 } from 'lucide-react';

interface NavbarProps {
  onNewScan: () => void;
  hasActiveAnalysis: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onNewScan, hasActiveAnalysis }) => {
  return (
    <header className="border-b border-surface-elevated bg-background/90 backdrop-blur-md sticky top-0 z-50 px-6 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-4 cursor-pointer" onClick={onNewScan}>
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-brand-violet to-brand-cyan/80 p-0.5 shadow-lg shadow-brand-violet/20">
            <div className="w-full h-full bg-background rounded-[10px] flex items-center justify-center">
              <Shield className="w-5 h-5 text-brand-cyan" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-black tracking-tight text-text-primary font-mono">PATCHPROOF</span>
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-brand-violet/20 text-brand-violet border border-brand-violet/40">
                v1.0 Security Agent
              </span>
            </div>
            <p className="text-xs text-text-secondary font-medium tracking-wide">
              Find the risk. Prove the fix.
            </p>
          </div>
        </div>

        {/* Center Ecosystem Support Badges */}
        <div className="hidden lg:flex items-center space-x-2 bg-surface/80 border border-surface-elevated px-3 py-1.5 rounded-full text-xs text-text-secondary">
          <span className="text-[11px] font-semibold text-text-secondary/70 uppercase tracking-wider mr-1">Ecosystems:</span>
          <span className="px-2 py-0.5 rounded-full bg-surface-elevated text-text-primary font-mono text-[11px]">PyPI</span>
          <span className="px-2 py-0.5 rounded-full bg-surface-elevated text-text-primary font-mono text-[11px]">npm</span>
          <span className="px-2 py-0.5 rounded-full bg-surface-elevated text-text-primary font-mono text-[11px]">Go</span>
          <span className="px-2 py-0.5 rounded-full bg-surface-elevated text-text-primary font-mono text-[11px]">Maven</span>
        </div>

        {/* Status Guard Indicator & Actions */}
        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1 rounded-lg bg-surface border border-surface-elevated text-xs font-mono">
            <div className="w-2 h-2 rounded-full bg-brand-cyan animate-pulse"></div>
            <span className="text-text-secondary">Auto-Merge:</span>
            <span className="text-severity-critical font-bold flex items-center gap-1">
              <Lock className="w-3 h-3 inline" /> Disabled (Guaranteed)
            </span>
          </div>

          {hasActiveAnalysis && (
            <button
              onClick={onNewScan}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-surface-elevated hover:bg-surface border border-brand-violet/30 text-text-primary transition-colors shadow-sm"
            >
              <Terminal className="w-3.5 h-3.5 text-brand-violet" />
              <span>New Analysis</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
