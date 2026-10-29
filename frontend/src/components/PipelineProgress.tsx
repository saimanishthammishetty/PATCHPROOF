import React from 'react';
import { CheckCircle2, Loader2, ArrowRight } from 'lucide-react';

interface PipelineProgressProps {
  currentStage: string;
  isComplete: boolean;
}

const STAGES = [
  'Input Validation',
  'Repo Retrieval',
  'Dependency Parsing',
  'SBOM Generation',
  'OSV.dev Lookup',
  'Secret Scanning',
  'Health & Typosquat',
  'Risk Scoring',
  'Safe Remediation'
];

export const PipelineProgress: React.FC<PipelineProgressProps> = ({ isComplete }) => {
  return (
    <div className="bg-surface/70 border border-surface-elevated rounded-xl p-4 my-6 shadow-inner">
      <div className="flex items-center justify-between mb-3 text-xs">
        <span className="font-mono text-brand-cyan uppercase tracking-wider flex items-center gap-1.5 font-bold">
          {isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-severity-low" />
          ) : (
            <Loader2 className="w-4 h-4 text-brand-cyan animate-spin" />
          )}
          {isComplete ? 'Analysis Pipeline Completed' : 'Autonomous Security Pipeline Executing...'}
        </span>
        <span className="text-text-secondary text-[11px] font-mono">
          Strict Evidence Verification Active
        </span>
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-9 gap-2">
        {STAGES.map((stage, idx) => (
          <div
            key={stage}
            className={`flex flex-col items-center justify-center p-2 rounded-lg text-center transition-all ${
              isComplete
                ? 'bg-surface-elevated/70 border border-brand-violet/30 text-text-primary'
                : idx < 5
                ? 'bg-surface-elevated/90 border border-brand-cyan/40 text-brand-cyan'
                : 'bg-surface/40 border border-surface-elevated text-text-secondary/50'
            }`}
          >
            <span className="text-[10px] font-mono text-text-secondary mb-1">0{idx + 1}</span>
            <span className="text-[11px] font-medium leading-tight">{stage}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

