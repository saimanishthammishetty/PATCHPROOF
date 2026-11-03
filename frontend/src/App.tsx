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
  CheckCircle, Lock, Bug, KeyRound, Layers, Wrench, History, Cpu, AlertTriangle, Code2
} from 'lucide-react';

export function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [demos, setDemos] = useState<DemoRepositoryInfo[]>([]);
  const [loading, setLoading] = useState(false);
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

  const handleStartScan = async (targetUrl?: string) => {
    const urlToScan = targetUrl || repoUrl;
    if (!urlToScan.trim()) {
      setError('Please provide a valid GitHub repository URL or choose a demo fixture.');
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

  return (
    <div className="min-h-screen bg-background text-text-primary flex flex-col font-sans selection:bg-brand-violet/30 selection:text-brand-cyan">
      <Navbar 
        onNewScan={handleResetScan} 
        hasActiveAnalysis={!!analysisResult}
        activeMode={appMode}
        onSelectMode={(mode) => setAppMode(mode)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 space-y-8">
        {appMode === 'debugger' ? (
          <DebuggerTab />
        ) : !analysisResult ? (
          /* ============================================================ */
          /* LANDING SCREEN / REPOSITORY INPUT */
          /* ============================================================ */
          <div className="space-y-12 py-6">
            {/* Hero Section */}
            <div className="text-center space-y-4 max-w-3xl mx-auto">
              <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-surface border border-brand-violet/30 text-xs font-mono text-brand-cyan shadow-sm">
                <Sparkles className="w-3.5 h-3.5 text-brand-violet" />
                <span>Autonomous Supply-Chain Security & Human-Verified Fixes</span>
              </div>

              <h1 className="text-4xl md:text-5xl font-black tracking-tight text-text-primary font-mono leading-tight">
                Find the risk. <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-violet via-brand-cyan to-brand-violet">Prove the fix.</span>
              </h1>

              <p className="text-sm md:text-base text-text-secondary leading-relaxed font-sans max-w-2xl mx-auto">
                PATCHPROOF inspects your GitHub repositories for vulnerable dependencies, suspicious packages, and committed secrets, generating verifiable CycloneDX SBOMs and safe, human-reviewed GitHub draft pull requests.
              </p>
            </div>

            {/* Input Console */}
            <div className="max-w-3xl mx-auto bg-surface border border-surface-elevated rounded-2xl p-6 shadow-2xl relative overflow-hidden">
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-mono font-bold uppercase tracking-wider text-text-secondary flex items-center justify-between">
                    <span>Target Repository URL</span>
                    <span className="text-[11px] text-text-secondary/60 lowercase">https://github.com/owner/repo</span>
                  </label>
                  <div className="relative">
                    <Search className="w-5 h-5 text-text-secondary absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="https://github.com/owner/repository"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && !loading && handleStartScan()}
                      className="w-full bg-surface-elevated border border-surface-elevated rounded-xl pl-11 pr-4 py-3 text-sm text-text-primary font-mono placeholder:text-text-secondary/40 focus:outline-none focus:border-brand-cyan/60 transition-colors shadow-inner"
                    />
                  </div>
                </div>

                {error && (
                  <div className="p-3 bg-severity-critical/15 border border-severity-critical/30 rounded-xl text-severity-critical text-xs font-mono flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
                  <div className="flex items-center space-x-2 text-xs text-text-secondary font-mono">
                    <Lock className="w-3.5 h-3.5 text-brand-cyan" />
                    <span>Read-only analysis • Never merges PRs</span>
                  </div>

                  <button
                    onClick={() => handleStartScan()}
                    disabled={loading}
                    className="w-full sm:w-auto flex items-center justify-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-brand-violet to-brand-cyan text-white text-xs font-bold uppercase font-mono tracking-wider shadow-lg shadow-brand-violet/25 hover:opacity-95 disabled:opacity-50 transition-all"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Analyzing Pipeline...</span>
                      </>
                    ) : (
                      <>
                        <Terminal className="w-4 h-4" />
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
                <span className="text-[11px] font-mono text-brand-cyan">Immediate test verification</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {demos.map((demo) => (
                  <div
                    key={demo.id}
                    onClick={() => handleSelectDemo(demo)}
                    className="p-4 rounded-xl bg-surface border border-surface-elevated hover:border-brand-violet/50 hover:bg-surface-elevated/70 transition-all cursor-pointer font-mono text-xs shadow-md group"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-text-primary group-hover:text-brand-cyan transition-colors">
                        {demo.name}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-surface-elevated text-brand-violet border border-brand-violet/30">
                        {demo.ecosystem}
                      </span>
                    </div>
                    <p className="text-[11px] text-text-secondary line-clamp-2 leading-relaxed mb-2 font-sans">
                      {demo.description}
                    </p>
                    <div className="text-[10px] text-brand-cyan flex items-center justify-between pt-1 border-t border-surface-elevated/60">
                      <span>Expected: {demo.expected_findings}</span>
                      <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Feature Overview Cards */}
            <div className="max-w-4xl mx-auto pt-6 border-t border-surface-elevated grid grid-cols-1 md:grid-cols-3 gap-6 font-mono text-xs">
              <div className="bg-surface/60 border border-surface-elevated rounded-xl p-4 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-brand-cyan/20 flex items-center justify-center text-brand-cyan">
                  <Layers className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-text-primary text-sm font-mono">Real SBOM Generation</h3>
                <p className="text-[11px] text-text-secondary font-sans leading-relaxed">
                  Extracts full direct and transitive dependencies into standard CycloneDX 1.5 & SPDX 2.3 JSON documents.
                </p>
              </div>

              <div className="bg-surface/60 border border-surface-elevated rounded-xl p-4 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-severity-critical/20 flex items-center justify-center text-severity-critical">
                  <Bug className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-text-primary text-sm font-mono">Deduplicated Advisories</h3>
                <p className="text-[11px] text-text-secondary font-sans leading-relaxed">
                  Real-time OSV.dev queries enriched with CISA KEV weaponization indicators and EPSS exploitation probabilities.
                </p>
              </div>

              <div className="bg-surface/60 border border-surface-elevated rounded-xl p-4 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-brand-violet/20 flex items-center justify-center text-brand-violet">
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
            <div className="flex items-center space-x-1.5 overflow-x-auto pb-2 border-b border-surface-elevated font-mono text-xs">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold transition-all whitespace-nowrap ${
                  activeTab === 'dashboard'
                    ? 'bg-surface-elevated text-brand-cyan border border-brand-cyan/40 shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                }`}
              >
                <Shield className="w-4 h-4" />
                <span>Security Dashboard</span>
              </button>

              <button
                onClick={() => setActiveTab('sbom')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold transition-all whitespace-nowrap ${
                  activeTab === 'sbom'
                    ? 'bg-surface-elevated text-brand-cyan border border-brand-cyan/40 shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                }`}
              >
                <Layers className="w-4 h-4" />
                <span>SBOM Inventory ({analysisResult.total_components})</span>
              </button>

              <button
                onClick={() => setActiveTab('vulnerabilities')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold transition-all whitespace-nowrap ${
                  activeTab === 'vulnerabilities'
                    ? 'bg-surface-elevated text-severity-critical border border-severity-critical/40 shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                }`}
              >
                <Bug className="w-4 h-4" />
                <span>Vulnerabilities ({analysisResult.vulnerabilities.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('secrets')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold transition-all whitespace-nowrap ${
                  activeTab === 'secrets'
                    ? 'bg-surface-elevated text-brand-cyan border border-brand-cyan/40 shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                }`}
              >
                <KeyRound className="w-4 h-4" />
                <span>Secrets ({analysisResult.secret_findings_count})</span>
              </button>

              <button
                onClick={() => setActiveTab('risk')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold transition-all whitespace-nowrap ${
                  activeTab === 'risk'
                    ? 'bg-surface-elevated text-brand-violet border border-brand-violet/40 shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                }`}
              >
                <Cpu className="w-4 h-4" />
                <span>Risk & Health ({analysisResult.health_findings.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('remediation')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold transition-all whitespace-nowrap ${
                  activeTab === 'remediation'
                    ? 'bg-surface-elevated text-brand-violet border border-brand-violet/40 shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                }`}
              >
                <Wrench className="w-4 h-4" />
                <span>Remediations ({analysisResult.remediations.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('audit')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold transition-all whitespace-nowrap ${
                  activeTab === 'audit'
                    ? 'bg-surface-elevated text-brand-cyan border border-brand-cyan/40 shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                }`}
              >
                <History className="w-4 h-4" />
                <span>Audit Trail ({analysisResult.audit_logs.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('debugger')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold transition-all whitespace-nowrap ${
                  activeTab === 'debugger'
                    ? 'bg-surface-elevated text-brand-violet border border-brand-violet/40 shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                }`}
              >
                <Code2 className="w-4 h-4 text-brand-cyan" />
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
