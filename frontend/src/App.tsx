import React, { useState, useEffect } from 'react';
import type {
  AnalysisResult, DemoRepositoryInfo, RemediationProposal
} from './types';
import { fetchDemos, startAnalysis, getAnalysis } from './services/api';
import { Navbar } from './components/Navbar';
import { PipelineProgress } from './components/PipelineProgress';
import { DashboardTab } from './components/DashboardTab';
import { SBOMTab } from './components/SBOMTab';
import { VulnerabilitiesTab } from './components/VulnerabilitiesTab';
import { SecretsTab } from './components/SecretsTab';
import { RiskEngineTab } from './components/RiskEngineTab';
import { RemediationTab } from './components/RemediationTab';
import { DraftPRModal } from './components/DraftPRModal';
import { AuditTab } from './components/AuditTab';
import { DebuggerTab } from './components/DebuggerTab';
import {
  Shield, Terminal, Search, ArrowRight, Loader2, Sparkles,
  CheckCircle, Lock, Bug, KeyRound, Layers, Wrench, History, Cpu,
  AlertTriangle, Code2, GitBranch, ShieldCheck, Zap
} from 'lucide-react';

const SCAN_SIMULATED_STAGES = [
  'Input & SSRF Validation',
  'Repository Retrieval & Tree Clone',
  'Multi-Ecosystem Dependency Extraction',
  'CycloneDX & SPDX SBOM Assembly',
  'Real-Time OSV.dev Advisory Correlation',
  'Regex & Entropy Secret Scan',
  'Package Health & Typosquat Analysis',
  'Explainable Risk Scoring Engine',
  'Safe Minimal Version Bump & Diff Gen'
];

export function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [demos, setDemos] = useState<DemoRepositoryInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [simulatedStageIdx, setSimulatedStageIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [appMode, setAppMode] = useState<'scanner' | 'debugger'>('scanner');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'sbom' | 'vulnerabilities' | 'secrets' | 'risk' | 'remediation' | 'audit' | 'debugger'>('dashboard');
  const [activeDraftProposal, setActiveDraftProposal] = useState<RemediationProposal | null>(null);

  useEffect(() => {
    fetchDemos()
      .then(setDemos)
      .catch(() => {});
  }, []);

  // Progress simulation during scanning
  useEffect(() => {
    let interval: any;
    if (loading) {
      setSimulatedStageIdx(0);
      interval = setInterval(() => {
        setSimulatedStageIdx(prev => (prev < SCAN_SIMULATED_STAGES.length - 1 ? prev + 1 : prev));
      }, 1200);
    } else {
      setSimulatedStageIdx(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleStartScan = async (targetUrl?: string) => {
    const urlToScan = targetUrl || repoUrl;
    if (!urlToScan.trim()) {
      setError('Please provide a valid GitHub repository URL or choose an interactive demo scenario.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await startAnalysis(urlToScan.trim(), branch.trim() || undefined);
      setAnalysisResult(result);
      setActiveTab('dashboard');
    } catch (err: any) {
      setError(err.message || 'Analysis failed. Please check repository URL or accessibility.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDemo = (demo: DemoRepositoryInfo) => {
    setRepoUrl(demo.url);
    handleStartScan(demo.url);
  };

  const handleResetScan = () => {
    setAnalysisResult(null);
    setRepoUrl('');
    setBranch('');
    setError(null);
  };

  const refreshAnalysis = async () => {
    if (analysisResult) {
      try {
        const refreshed = await getAnalysis(analysisResult.id);
        setAnalysisResult(refreshed);
      } catch (err) {}
    }
  };

  const critVulnCount = analysisResult?.vulnerabilities.filter(v => v.severity === 'CRITICAL' || v.cisa_kev).length || 0;

  return (
    <div className="min-h-screen bg-background text-text-primary flex flex-col font-sans selection:bg-accent-emerald/30 selection:text-text-primary">
      <Navbar
        onNewScan={handleResetScan}
        hasActiveAnalysis={!!analysisResult}
        repoName={analysisResult?.repo_name}
        activeMode={appMode}
        onSelectMode={(mode) => setAppMode(mode)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 md:p-8 space-y-8">
        {appMode === 'debugger' ? (
          <DebuggerTab />
        ) : !analysisResult ? (
          /* ============================================================ */
          /* LANDING SCREEN / REPOSITORY INPUT */
          /* ============================================================ */
          <div className="space-y-10 py-4 sm:py-6">
            {/* Hero Section */}
            <div className="text-center space-y-3.5 max-w-3xl mx-auto">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-md bg-surface border border-surface-border text-xs font-mono text-text-secondary">
                <Sparkles className="w-3.5 h-3.5 text-accent-emerald" />
                <span>Autonomous Supply-Chain Security & Human-Verified Fixes</span>
              </div>

              <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-text-primary font-mono leading-tight">
                Find the risk. <span className="text-accent-emerald">Prove the fix.</span>
              </h1>

              <p className="text-sm md:text-base text-text-secondary leading-relaxed font-sans max-w-2xl mx-auto">
                PATCHPROOF inspects your GitHub repositories for vulnerable dependencies, suspicious packages, and committed secrets, generating verifiable CycloneDX SBOMs and safe, human-reviewed GitHub draft pull requests.
              </p>
            </div>

            {/* Input Console */}
            <div className="max-w-3xl mx-auto bg-surface border border-surface-border rounded-lg p-6 relative overflow-hidden">
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="md:col-span-2 space-y-1.5">
                    <label className="text-xs font-mono font-bold uppercase tracking-wider text-text-secondary flex items-center justify-between">
                      <span>Target Repository URL</span>
                      <span className="text-[11px] text-text-secondary/60 lowercase">https://github.com/owner/repo</span>
                    </label>
                    <div className="relative">
                      <Search className="w-4 h-4 text-text-secondary absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="https://github.com/owner/repository"
                        value={repoUrl}
                        onChange={(e) => setRepoUrl(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !loading && handleStartScan()}
                        disabled={loading}
                        className="w-full bg-background-secondary border border-surface-border rounded-md pl-10 pr-4 py-2.5 text-xs sm:text-sm text-text-primary font-mono placeholder:text-text-muted focus:outline-none focus:border-accent-emerald transition-colors"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-mono font-bold uppercase tracking-wider text-text-secondary flex items-center justify-between">
                      <span>Branch (Optional)</span>
                      <span className="text-[11px] text-text-secondary/60 lowercase">default: main</span>
                    </label>
                    <div className="relative">
                      <GitBranch className="w-4 h-4 text-text-secondary absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="main"
                        value={branch}
                        onChange={(e) => setBranch(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !loading && handleStartScan()}
                        disabled={loading}
                        className="w-full bg-background-secondary border border-surface-border rounded-md pl-10 pr-4 py-2.5 text-xs sm:text-sm text-text-primary font-mono placeholder:text-text-muted focus:outline-none focus:border-accent-emerald transition-colors"
                      />
                    </div>
                  </div>
                </div>

                {error && (
                  <div className="p-3.5 bg-severity-critical/10 border border-severity-critical/30 rounded-md text-severity-critical text-xs font-mono flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                {/* Live Scanning Progress Box when Loading */}
                {loading && (
                  <div className="p-4 rounded-md bg-background-secondary border border-surface-border space-y-3 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-accent-emerald font-semibold flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Autonomous Pipeline Executing...</span>
                      </span>
                      <span className="text-text-secondary text-[11px]">
                        Stage {simulatedStageIdx + 1} of {SCAN_SIMULATED_STAGES.length}
                      </span>
                    </div>

                    <div className="w-full bg-surface rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-accent-emerald h-full transition-all duration-700 rounded-full"
                        style={{ width: `${((simulatedStageIdx + 1) / SCAN_SIMULATED_STAGES.length) * 100}%` }}
                      />
                    </div>

                    <div className="text-text-primary text-[11px] flex items-center gap-1.5">
                      <span className="text-accent-emerald">▶</span>
                      <span>{SCAN_SIMULATED_STAGES[simulatedStageIdx]}</span>
                    </div>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-1">
                  <div className="flex items-center space-x-2 text-xs text-text-secondary font-mono">
                    <Lock className="w-3.5 h-3.5 text-accent-emerald" />
                    <span>Read-only analysis • Never merges PRs (Guaranteed)</span>
                  </div>

                  <button
                    onClick={() => handleStartScan()}
                    disabled={loading}
                    className="w-full sm:w-auto flex items-center justify-center space-x-2 px-5 py-2.5 rounded-md bg-accent-emerald hover:bg-accent-emerald-hover text-white text-xs font-semibold uppercase font-mono tracking-wider disabled:opacity-50 transition-colors cursor-pointer group"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Analyzing Pipeline...</span>
                      </>
                    ) : (
                      <>
                        <Terminal className="w-4 h-4 group-hover:scale-105 transition-transform" />
                        <span>Analyze Repository</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Demo Fixture Quick Loaders */}
            <div className="max-w-4xl mx-auto space-y-3">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-text-secondary">
                  One-Click Interactive Demo Scenarios:
                </span>
                <span className="text-[11px] font-mono text-text-secondary">Immediate test verification</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {demos.map((demo) => (
                  <div
                    key={demo.id}
                    onClick={() => !loading && handleSelectDemo(demo)}
                    className="p-4 rounded-lg bg-surface border border-surface-border hover:border-surface-border/80 hover:bg-surface-elevated transition-colors cursor-pointer font-mono text-xs group"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-text-primary group-hover:text-accent-emerald transition-colors">
                        {demo.name}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-surface-elevated text-text-secondary border border-surface-border uppercase">
                        {demo.ecosystem}
                      </span>
                    </div>
                    <p className="text-[11px] text-text-secondary line-clamp-2 leading-relaxed mb-2 font-sans">
                      {demo.description}
                    </p>
                    <div className="text-[10px] text-accent-emerald flex items-center justify-between pt-1 border-t border-surface-border">
                      <span>Expected: {demo.expected_findings}</span>
                      <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Feature Overview Cards */}
            <div className="max-w-4xl mx-auto pt-6 border-t border-surface-border grid grid-cols-1 md:grid-cols-3 gap-5 font-mono text-xs">
              <div className="bg-surface border border-surface-border rounded-lg p-5 space-y-2.5">
                <div className="w-8 h-8 rounded-md bg-surface-elevated border border-surface-border flex items-center justify-center text-accent-emerald">
                  <Layers className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-text-primary text-sm font-mono">Real SBOM Generation</h3>
                <p className="text-[11px] text-text-secondary font-sans leading-relaxed">
                  Extracts full direct and transitive dependencies into standard CycloneDX 1.5 & SPDX 2.3 JSON documents.
                </p>
              </div>

              <div className="bg-surface border border-surface-border rounded-lg p-5 space-y-2.5">
                <div className="w-8 h-8 rounded-md bg-surface-elevated border border-surface-border flex items-center justify-center text-severity-critical">
                  <Bug className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-text-primary text-sm font-mono">Deduplicated Advisories</h3>
                <p className="text-[11px] text-text-secondary font-sans leading-relaxed">
                  Real-time OSV.dev queries enriched with CISA KEV weaponization indicators and EPSS exploitation probabilities.
                </p>
              </div>

              <div className="bg-surface border border-surface-border rounded-lg p-5 space-y-2.5">
                <div className="w-8 h-8 rounded-md bg-surface-elevated border border-surface-border flex items-center justify-center text-accent-amber">
                  <Wrench className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-text-primary text-sm font-mono">Safe Draft PRs Only</h3>
                <p className="text-[11px] text-text-secondary font-sans leading-relaxed">
                  Calculates minimum safe version bumps with manifest diffs. Strict architectural guarantee: Never auto-merges.
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* ============================================================ */
          /* ACTIVE ANALYSIS DASHBOARD */
          /* ============================================================ */
          <div className="space-y-6">
            {/* Pipeline Stage Indicators */}
            <PipelineProgress
              currentStage={analysisResult.stage}
              isComplete={analysisResult.status === 'completed'}
            />

            {/* Navigation Tabs Bar */}
            <div className="flex items-center space-x-1.5 overflow-x-auto pb-2 border-b border-surface-border font-mono text-xs">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-md font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activeTab === 'dashboard'
                    ? 'bg-surface-elevated text-text-primary border border-surface-border'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent'
                }`}
              >
                <Shield className="w-4 h-4 text-accent-emerald" />
                <span>Security Dashboard</span>
              </button>

              <button
                onClick={() => setActiveTab('sbom')}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-md font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activeTab === 'sbom'
                    ? 'bg-surface-elevated text-text-primary border border-surface-border'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent'
                }`}
              >
                <Layers className="w-4 h-4" />
                <span>SBOM Inventory</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-background-secondary border border-surface-border text-text-secondary">
                  {analysisResult.total_components}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('vulnerabilities')}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-md font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activeTab === 'vulnerabilities'
                    ? 'bg-surface-elevated text-text-primary border border-surface-border'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent'
                }`}
              >
                <Bug className="w-4 h-4 text-severity-critical" />
                <span>Vulnerabilities</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  critVulnCount > 0 ? 'bg-severity-critical/20 text-severity-critical border border-severity-critical/30' : 'bg-background-secondary border border-surface-border text-text-secondary'
                }`}>
                  {analysisResult.vulnerabilities.length}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('secrets')}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-md font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activeTab === 'secrets'
                    ? 'bg-surface-elevated text-text-primary border border-surface-border'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent'
                }`}
              >
                <KeyRound className="w-4 h-4 text-accent-amber" />
                <span>Secrets</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  analysisResult.secret_findings_count > 0 ? 'bg-severity-critical/20 text-severity-critical border border-severity-critical/30' : 'bg-background-secondary border border-surface-border text-severity-low'
                }`}>
                  {analysisResult.secret_findings_count}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('risk')}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-md font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activeTab === 'risk'
                    ? 'bg-surface-elevated text-text-primary border border-surface-border'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent'
                }`}
              >
                <Cpu className="w-4 h-4 text-accent-emerald" />
                <span>Risk & Health</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-background-secondary border border-surface-border text-text-secondary font-medium">
                  {analysisResult.risk_overview.score}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('remediation')}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-md font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activeTab === 'remediation'
                    ? 'bg-surface-elevated text-text-primary border border-surface-border'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent'
                }`}
              >
                <Wrench className="w-4 h-4 text-accent-emerald" />
                <span>Remediations</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-accent-emerald/15 text-accent-emerald border border-accent-emerald/30 font-medium">
                  {analysisResult.remediations.length}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('audit')}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-md font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activeTab === 'audit'
                    ? 'bg-surface-elevated text-text-primary border border-surface-border'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent'
                }`}
              >
                <History className="w-4 h-4" />
                <span>Audit Trail</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-background-secondary border border-surface-border text-text-secondary">
                  {analysisResult.audit_logs.length}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('debugger')}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-md font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activeTab === 'debugger'
                    ? 'bg-surface-elevated text-text-primary border border-surface-border'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent'
                }`}
              >
                <Code2 className="w-4 h-4 text-accent-emerald" />
                <span>Code Debugger</span>
              </button>
            </div>

            {/* Active Tab View */}
            {activeTab === 'dashboard' && (
              <DashboardTab data={analysisResult} onSelectTab={(tab: any) => setActiveTab(tab)} />
            )}
            {activeTab === 'sbom' && (
              <SBOMTab analysisId={analysisResult.id} components={analysisResult.components} />
            )}
            {activeTab === 'vulnerabilities' && (
              <VulnerabilitiesTab vulnerabilities={analysisResult.vulnerabilities} />
            )}
            {activeTab === 'secrets' && (
              <SecretsTab secrets={analysisResult.secrets} />
            )}
            {activeTab === 'risk' && (
              <RiskEngineTab data={analysisResult} />
            )}
            {activeTab === 'remediation' && (
              <RemediationTab
                remediations={analysisResult.remediations}
                onOpenDraftModal={(prop) => setActiveDraftProposal(prop)}
              />
            )}
            {activeTab === 'audit' && (
              <AuditTab logs={analysisResult.audit_logs} />
            )}
            {activeTab === 'debugger' && (
              <DebuggerTab />
            )}

            {/* Draft PR Review Modal */}
            {activeDraftProposal && (
              <DraftPRModal
                analysisId={analysisResult.id}
                repoUrl={analysisResult.repo_url}
                proposal={activeDraftProposal}
                onClose={() => setActiveDraftProposal(null)}
                onSuccess={refreshAnalysis}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
export default App;
