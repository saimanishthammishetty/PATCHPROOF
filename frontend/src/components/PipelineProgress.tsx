import React from 'react';
import { CheckCircle2, Loader2, ShieldCheck } from 'lucide-react';

interface PipelineProgressProps {
  currentStage: string;
  isComplete: boolean;
}

const STAGES = [
  { id: 'validation', label: 'Input Validation', desc: 'SSRF & URL Guard' },
  { id: 'retrieval', label: 'Repo Retrieval', desc: 'Tree Clone & Parse' },
  { id: 'dependencies', label: 'Dependency Parsing', desc: 'Multi-Ecosystem' },
  { id: 'sbom', label: 'SBOM Generation', desc: 'CycloneDX & SPDX' },
  { id: 'osv', label: 'OSV.dev Lookup', desc: 'Advisory Correlation' },
  { id: 'secrets', label: 'Secret Scanning', desc: 'Entropy & Regex' },
  { id: 'health', label: 'Health & Typosquat', desc: 'Ecosystem Heuristics' },
  { id: 'risk', label: 'Risk Scoring', desc: 'Explainable Formula' },
  { id: 'remediation', label: 'Safe Remediation', desc: 'Unified Diff Gen' }
];

export const PipelineProgress: React.FC<PipelineProgressProps> = ({ currentStage, isComplete }) => {
  const stageIndex = isComplete
    ? STAGES.length
    : STAGES.findIndex(s => s.label.toLowerCase() === currentStage.toLowerCase() || s.id === currentStage.toLowerCase());

  const activeIdx = stageIndex >= 0 ? stageIndex : 4;

  return (
    <div className="bg-surface border border-surface-border rounded-lg p-3.5 sm:p-4 text-xs font-mono">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div className="flex items-center space-x-2">
          {isComplete ? (
            <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-accent-emerald-muted text-accent-emerald border border-accent-emerald/30 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Pipeline Analysis Complete</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-surface-elevated text-text-primary border border-surface-border font-medium">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-emerald" />
              <span>Stage: {currentStage || 'Pipeline Executing...'}</span>
            </span>
          )}
          <span className="text-text-muted text-[11px] hidden md:inline">
            • 9 Evidence Stages
          </span>
        </div>

        <div className="flex items-center space-x-1.5 text-[11px] text-text-secondary">
          <ShieldCheck className="w-3.5 h-3.5 text-accent-emerald" />
          <span>Strict Evidence Verification • Zero Hallucinations</span>
        </div>
      </div>

      {/* Progress Track */}
      <div className="grid grid-cols-3 sm:grid-cols-9 gap-1.5">
        {STAGES.map((stage, idx) => {
          const isPast = isComplete || idx < activeIdx;
          const isCurrent = !isComplete && idx === activeIdx;

          return (
            <div
              key={stage.id}
              className={`flex flex-col items-center justify-center p-2 rounded-md text-center border transition-colors ${
                isPast
                  ? 'bg-background-secondary border-surface-border text-text-primary'
                  : isCurrent
                  ? 'bg-surface-elevated border-accent-emerald/50 text-text-primary'
                  : 'bg-background/40 border-surface-border/40 text-text-muted'
              }`}
            >
              <div className="flex items-center justify-center space-x-1 mb-1">
                {isPast ? (
                  <CheckCircle2 className="w-3 h-3 text-accent-emerald shrink-0" />
                ) : isCurrent ? (
                  <Loader2 className="w-3 h-3 text-accent-emerald animate-spin shrink-0" />
                ) : (
                  <span className="text-[9px] font-mono opacity-40">0{idx + 1}</span>
                )}
              </div>
              <span className="text-[10px] font-medium leading-tight truncate w-full">
                {stage.label}
              </span>
              <span className="text-[8px] text-text-muted hidden xl:block mt-0.5 truncate w-full">
                {stage.desc}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
