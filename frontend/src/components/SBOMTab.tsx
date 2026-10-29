import React, { useState } from 'react';
import type { Component } from '../types';
import { Download, Search, Filter, Box, ShieldCheck, AlertCircle, ArrowUpDown } from 'lucide-react';
import { downloadSBOM } from '../services/api';

interface SBOMTabProps {
  analysisId: string;
  components: Component[];
}

export const SBOMTab: React.FC<SBOMTabProps> = ({ analysisId, components }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [ecosystemFilter, setEcosystemFilter] = useState('all');
  const [scopeFilter, setScopeFilter] = useState('all');
  const [exporting, setExporting] = useState<string | null>(null);

  const filteredComponents = components.filter(c => {
    const matchesSearch = c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.version.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.purl.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesEco = ecosystemFilter === 'all' || c.ecosystem.toLowerCase() === ecosystemFilter.toLowerCase();
    const matchesScope = scopeFilter === 'all' || (scopeFilter === 'direct' ? c.direct : !c.direct);
    return matchesSearch && matchesEco && matchesScope;
  });

  const handleExport = async (format: 'cyclonedx' | 'spdx') => {
    try {
      setExporting(format);
      await downloadSBOM(analysisId, format);
    } catch (err: any) {
      alert(`Export error: ${err.message}`);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Header & Exports */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface border border-surface-elevated rounded-2xl p-5 shadow-xl">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <Box className="w-5 h-5 text-brand-cyan" />
            Software Bill of Materials (SBOM) Explorer
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Standardized component inventory with package URLs (PURLs), license metadata, and scope classification.
          </p>
        </div>

        {/* SBOM Export Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleExport('cyclonedx')}
            disabled={exporting !== null}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-surface-elevated hover:bg-surface border border-brand-violet/40 text-text-primary text-xs font-mono font-semibold transition-colors shadow-sm disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5 text-brand-violet" />
            <span>{exporting === 'cyclonedx' ? 'Exporting...' : 'CycloneDX 1.5 JSON'}</span>
          </button>

          <button
            onClick={() => handleExport('spdx')}
            disabled={exporting !== null}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-surface-elevated hover:bg-surface border border-brand-cyan/40 text-text-primary text-xs font-mono font-semibold transition-colors shadow-sm disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5 text-brand-cyan" />
            <span>{exporting === 'spdx' ? 'Exporting...' : 'SPDX 2.3 JSON'}</span>
          </button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-surface/80 border border-surface-elevated p-3 rounded-xl">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search package name, version, or purl..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-surface-elevated border border-surface-elevated rounded-lg pl-9 pr-4 py-2 text-xs text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-brand-cyan/50 font-mono"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <select
            value={ecosystemFilter}
            onChange={(e) => setEcosystemFilter(e.target.value)}
            className="bg-surface-elevated border border-surface-elevated rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-brand-cyan/50 font-mono"
          >
            <option value="all">All Ecosystems</option>
            <option value="pypi">PyPI (Python)</option>
            <option value="npm">npm (Node/TS)</option>
            <option value="golang">Go Modules</option>
            <option value="maven">Maven (Java)</option>
          </select>

          <select
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value)}
            className="bg-surface-elevated border border-surface-elevated rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-brand-cyan/50 font-mono"
          >
            <option value="all">All Scopes</option>
            <option value="direct">Direct Only</option>
            <option value="transitive">Transitive Only</option>
          </select>
        </div>
      </div>

      {/* Component Table */}
      <div className="bg-surface border border-surface-elevated rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-surface-elevated bg-surface-elevated/40 text-text-secondary font-mono uppercase text-[11px] tracking-wider">
                <th className="py-3 px-4">Component</th>
                <th className="py-3 px-4">Ecosystem</th>
                <th className="py-3 px-4">Installed Version</th>
                <th className="py-3 px-4">Scope</th>
                <th className="py-3 px-4">License</th>
                <th className="py-3 px-4">Manifest Path</th>
                <th className="py-3 px-4">Vulnerabilities</th>
                <th className="py-3 px-4">Component Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-elevated font-mono">
              {filteredComponents.map((c) => (
                <tr key={`${c.ecosystem}-${c.name}-${c.version}`} className="hover:bg-surface-elevated/30 transition-colors">
                  <td className="py-3 px-4">
                    <div className="space-y-0.5">
                      <span className="font-bold text-text-primary">{c.name}</span>
                      <div className="text-[10px] text-text-secondary/80 truncate max-w-xs">{c.purl}</div>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded bg-surface-elevated text-brand-cyan text-[11px] font-semibold uppercase">
                      {c.ecosystem}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-text-primary font-semibold">{c.version}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      c.direct 
                        ? 'bg-brand-violet/20 text-brand-violet border border-brand-violet/30' 
                        : 'bg-surface-elevated text-text-secondary'
                    }`}>
                      {c.direct ? 'Direct' : 'Transitive'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-text-secondary">{c.license || 'Unknown'}</td>
                  <td className="py-3 px-4 text-text-secondary text-[11px] truncate max-w-[140px]">{c.manifest_path}</td>
                  <td className="py-3 px-4">
                    {c.vulnerability_count > 0 ? (
                      <span className="px-2 py-0.5 rounded bg-severity-critical/20 text-severity-critical border border-severity-critical/30 font-bold">
                        {c.vulnerability_count} CVE{c.vulnerability_count > 1 ? 's' : ''}
                      </span>
                    ) : (
                      <span className="text-severity-low flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" /> Clean
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`font-bold ${
                      c.risk_score >= 70 ? 'text-severity-critical' : c.risk_score >= 40 ? 'text-severity-high' : 'text-severity-low'
                    }`}>
                      {c.risk_score.toFixed(1)}/100
                    </span>
                  </td>
                </tr>
              ))}

              {filteredComponents.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-text-secondary font-mono">
                    No components found matching your search criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
