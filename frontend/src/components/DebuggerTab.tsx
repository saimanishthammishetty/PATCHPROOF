import React, { useState } from 'react';
import type { CodeDebugResponse } from '../types';
import { analyzeCodeSnippet } from '../services/api';
import { 
  Bug, Sparkles, CheckCircle2, AlertTriangle, AlertCircle, 
  Terminal, ArrowRight, Loader2, Code2, Wrench, ShieldAlert, Info
} from 'lucide-react';

const PRESET_EXAMPLES = [
  {
    title: 'Python: Mutable Default Argument',
    language: 'python',
    code: `def process_batch(item, queue=[]):
    """Appends item to batch queue."""
    queue.append(item)
    return queue
`
  },
  {
    title: 'Python: Identity Comparison on Literal',
    language: 'python',
    code: `def verify_status(status_code):
    """Verifies HTTP response code."""
    if status_code is 200:
        return 'SUCCESS'
    return 'FAILURE'
`
  },
  {
    title: 'JavaScript: Loose Equality Coercion',
    language: 'javascript',
    code: `function checkUserStatus(val) {
    if (val == 0) {
        return 'EMPTY_OR_ZERO';
    }
    return 'POPULATED';
}
`
  },
  {
    title: 'Python: Clean Bug-Free Control',
    language: 'python',
    code: `def filter_positives(items):
    """Safely filters positive numeric items."""
    if not isinstance(items, (list, tuple)):
        raise TypeError('items must be a list or tuple')
    return [x for x in items if isinstance(x, (int, float)) and x > 0]
`
  }
];

export const DebuggerTab: React.FC = () => {
  const [code, setCode] = useState(PRESET_EXAMPLES[0].code);
  const [language, setLanguage] = useState(PRESET_EXAMPLES[0].language);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CodeDebugResponse | null>(null);

  const handleAnalyze = async () => {
    if (!code.trim()) {
      setError('Please provide source code to analyze.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const resp = await analyzeCodeSnippet(code, language);
      setResult(resp);
    } catch (err: any) {
      setError(err.message || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (preset: typeof PRESET_EXAMPLES[0]) => {
    setCode(preset.code);
    setLanguage(preset.language);
    setResult(null);
    setError(null);
  };

  const lines = code.split('\n');

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-surface border border-surface-elevated rounded-2xl p-6 shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="p-2 rounded-lg bg-brand-violet/20 text-brand-violet border border-brand-violet/30">
                <Bug className="w-5 h-5" />
              </span>
              <h2 className="text-xl font-black font-mono tracking-tight text-text-primary">
                AI Code Debugger & Defect Classifier
              </h2>
              <span className="px-2 py-0.5 text-[10px] font-bold font-mono rounded bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40">
                ML Pipeline v1.0
              </span>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed max-w-2xl">
              Inspects source code for archetype defect patterns, detects high-probability bugs across 13 calibrated categories, and proposes tested line-level remediations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-surface-elevated border border-brand-violet/40 text-text-primary font-mono text-xs px-3 py-2 rounded-xl focus:outline-none focus:border-brand-cyan transition-colors"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="c">C / C++</option>
              <option value="java">Java</option>
              <option value="go">Go</option>
            </select>

            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="flex items-center space-x-2 px-5 py-2 rounded-xl bg-brand-violet hover:bg-brand-violet/90 text-white font-mono text-xs font-bold shadow-lg shadow-brand-violet/25 disabled:opacity-50 transition-all cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-brand-cyan" />
                  <span>Analyze Code</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Example Presets */}
        <div className="mt-4 pt-4 border-t border-surface-elevated/70 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-mono font-bold text-text-secondary mr-1">Presets:</span>
          {PRESET_EXAMPLES.map((ex, idx) => (
            <button
              key={idx}
              onClick={() => handleSelectPreset(ex)}
              className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-surface-elevated hover:bg-surface-elevated/80 border border-surface-elevated hover:border-brand-cyan/40 text-text-secondary hover:text-brand-cyan transition-all"
            >
              {ex.title}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-severity-critical/10 border border-severity-critical/30 text-severity-critical flex items-center space-x-3 text-xs font-mono">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Editor & Results Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Left: Code Input Pane */}
        <div className="bg-surface border border-surface-elevated rounded-2xl overflow-hidden shadow-md flex flex-col h-[520px]">
          <div className="px-4 py-3 bg-surface-elevated/80 border-b border-surface-elevated flex items-center justify-between font-mono text-xs text-text-secondary">
            <div className="flex items-center space-x-2">
              <Code2 className="w-4 h-4 text-brand-cyan" />
              <span className="font-bold text-text-primary">Source Code Input</span>
            </div>
            <span>{lines.length} lines</span>
          </div>

          <div className="flex-1 flex overflow-hidden font-mono text-xs bg-background/50">
            {/* Line numbers gutter */}
            <div className="w-12 py-3 bg-surface/80 border-r border-surface-elevated/50 text-right pr-3 select-none text-text-secondary/40 font-mono">
              {lines.map((_, i) => (
                <div 
                  key={i} 
                  className={`leading-6 ${
                    result?.faulty_line_number === i + 1 
                      ? 'text-severity-critical font-bold' 
                      : ''
                  }`}
                >
                  {i + 1}
                </div>
              ))}
            </div>

            {/* Code text area */}
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste or write code here..."
              className="flex-1 p-3 bg-transparent text-text-primary resize-none focus:outline-none font-mono text-xs leading-6 overflow-y-auto whitespace-pre selection:bg-brand-violet/30"
              spellCheck={false}
            />
          </div>
        </div>

        {/* Right: Inspection & Remediation Pane */}
        <div className="space-y-6">
          {!result ? (
            <div className="h-[520px] bg-surface/60 border border-surface-elevated rounded-2xl flex flex-col items-center justify-center p-8 text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-brand-violet/10 border border-brand-violet/30 flex items-center justify-center text-brand-violet">
                <Terminal className="w-7 h-7" />
              </div>
              <div className="space-y-1.5 max-w-sm">
                <h3 className="font-bold font-mono text-text-primary text-sm">Awaiting Code Submission</h3>
                <p className="text-xs text-text-secondary leading-relaxed font-sans">
                  Select a language, write or paste a snippet, or choose an interactive preset to trigger archetype classification and line localization.
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-surface border border-surface-elevated rounded-2xl p-6 shadow-md space-y-5">
              {/* Status Header */}
              <div className="flex items-center justify-between pb-4 border-b border-surface-elevated">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-text-secondary">
                    Analysis Classification:
                  </span>
                  <div className="flex items-center space-x-2">
                    {result.issue_detected ? (
                      <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-severity-critical/20 text-severity-critical border border-severity-critical/40 font-mono text-xs font-bold">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        <span>Defect Identified</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-severity-low/20 text-severity-low border border-severity-low/40 font-mono text-xs font-bold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Clean Code Control</span>
                      </span>
                    )}

                    <span className="px-2.5 py-1 rounded-lg bg-surface-elevated border border-surface-elevated font-mono text-xs text-text-primary">
                      {result.category_label}
                    </span>
                  </div>
                </div>

                {/* Confidence Badge */}
                <div className="text-right">
                  <span className="text-[10px] font-mono text-text-secondary block">Model Confidence</span>
                  <span className="font-mono text-base font-bold text-brand-cyan">
                    {(result.confidence_score * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Faulty Line Alert if located */}
              {result.faulty_line_number && (
                <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/30 space-y-1 font-mono text-xs">
                  <div className="flex items-center justify-between text-severity-critical font-bold">
                    <span>Identified Defect at Line {result.faulty_line_number}</span>
                    <span className="text-[10px] uppercase tracking-wider bg-severity-critical/20 px-2 py-0.5 rounded">
                      AST Localized
                    </span>
                  </div>
                  {result.faulty_line_content && (
                    <div className="p-2 bg-background/80 rounded border border-surface-elevated text-text-primary text-[11px] overflow-x-auto">
                      <code>{result.faulty_line_content}</code>
                    </div>
                  )}
                </div>
              )}

              {/* Detailed Explanation */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-text-secondary">
                  Assessment:
                </span>
                <p className="text-xs text-text-primary leading-relaxed bg-surface-elevated/40 p-3 rounded-xl border border-surface-elevated">
                  {result.explanation}
                </p>
              </div>

              {/* Remediated Fix & Unified Diff if Available */}
              {result.diff && (
                <div className="space-y-2 pt-2 border-t border-surface-elevated">
                  <div className="flex items-center space-x-1.5 text-xs font-mono font-bold text-brand-cyan">
                    <Wrench className="w-3.5 h-3.5" />
                    <span>Verified Automated Remediation Diff:</span>
                  </div>
                  <pre className="p-3 rounded-xl bg-background border border-surface-elevated font-mono text-[11px] overflow-x-auto text-text-secondary leading-relaxed">
                    {result.diff.split('\n').map((line, idx) => {
                      if (line.startsWith('+') && !line.startsWith('+++')) {
                        return <span key={idx} className="text-severity-low block">{line}</span>;
                      }
                      if (line.startsWith('-') && !line.startsWith('---')) {
                        return <span key={idx} className="text-severity-critical block">{line}</span>;
                      }
                      return <span key={idx} className="block">{line}</span>;
                    })}
                  </pre>
                </div>
              )}

              {/* Honest Limitation Notice */}
              <div className="p-3 rounded-xl bg-surface-elevated/30 border border-surface-elevated/60 text-[10px] font-mono text-text-secondary flex items-start space-x-2">
                <Info className="w-3.5 h-3.5 shrink-0 text-brand-cyan mt-0.5" />
                <span>{result.limitations_notice}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
