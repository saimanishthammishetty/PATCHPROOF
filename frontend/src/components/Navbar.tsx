import React from 'react';
import { Shield, Lock, Terminal, Bug, GitBranch } from 'lucide-react';

interface NavbarProps {
  onNewScan: () => void;
  hasActiveAnalysis: boolean;
  repoName?: string;
  activeMode: 'scanner' | 'debugger';
  onSelectMode: (mode: 'scanner' | 'debugger') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onNewScan,
  hasActiveAnalysis,
  repoName,
  activeMode,
  onSelectMode
}) => {
  return (
    <header className="border-b border-surface-border bg-background sticky top-0 z-50 px-4 sm:px-6 py-2.5 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center space-x-3 cursor-pointer group select-none" onClick={onNewScan}>
          <div className="flex items-center justify-center w-8 h-8 rounded-md bg-surface border border-surface-border text-accent-emerald transition-colors group-hover:border-accent-emerald/60">
            <Shield className="w-4 h-4 text-accent-emerald" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-base font-bold tracking-tight text-text-primary font-mono">
              PATCHPROOF
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-surface-elevated text-text-secondary border border-surface-border">
              v1.0
            </span>
          </div>
        </div>

        {/* Center Mode Switcher Tabs */}
        <div className="flex items-center bg-surface border border-surface-border p-0.5 rounded-lg text-xs font-sans">
          <button
            onClick={() => onSelectMode('scanner')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-md transition-colors cursor-pointer text-xs ${
              activeMode === 'scanner'
                ? 'bg-surface-elevated text-text-primary font-medium border border-surface-border'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Shield className="w-3.5 h-3.5 text-accent-emerald" />
            <span className="hidden sm:inline">Supply Chain Scanner</span>
            <span className="sm:hidden">Scanner</span>
          </button>

          <button
            onClick={() => onSelectMode('debugger')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-md transition-colors cursor-pointer text-xs ${
              activeMode === 'debugger'
                ? 'bg-surface-elevated text-text-primary font-medium border border-surface-border'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Bug className="w-3.5 h-3.5 text-accent-amber" />
            <span className="hidden sm:inline">AI Code Debugger</span>
            <span className="sm:hidden">Debugger</span>
          </button>
        </div>

        {/* Status Guard Indicator & Actions */}
        <div className="flex items-center space-x-3">
          {/* Active Repo Pill if present */}
          {hasActiveAnalysis && repoName && (
            <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-surface border border-surface-border text-xs font-mono text-text-primary">
              <GitBranch className="w-3 h-3 text-text-secondary" />
              <span className="truncate max-w-[150px] font-medium">{repoName}</span>
            </div>
          )}

          {/* Safety Guarantee Lock */}
          <div
            className="hidden md:flex items-center space-x-2 px-2.5 py-1 rounded-md bg-surface border border-surface-border text-xs font-mono"
            title="NEVER_MERGE Safety Guarantee: PATCHPROOF will open only draft pull requests. Human code review and manual merge are permanently mandatory in the architecture."
          >
            <span className="w-1.5 h-1.5 rounded-full bg-accent-emerald"></span>
            <span className="text-text-secondary text-[11px]">Auto-Merge:</span>
            <span className="text-text-primary font-medium text-[11px] flex items-center gap-1">
              <Lock className="w-3 h-3 inline text-text-secondary" /> Disabled
            </span>
          </div>

          {hasActiveAnalysis && (
            <button
              onClick={onNewScan}
              className="flex items-center space-x-1.5 px-3 py-1 text-xs font-sans font-medium rounded-md bg-surface hover:bg-surface-elevated border border-surface-border text-text-primary transition-colors cursor-pointer"
            >
              <Terminal className="w-3.5 h-3.5 text-text-secondary" />
              <span>New Scan</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
