import React, { useState } from 'react';
import type { Component } from '../types';
import {
  Download, Search, Filter, Box, ShieldCheck, AlertCircle,
  ArrowUpDown, Copy, Check, Layers, AlertTriangle
} from 'lucide-react';
import { downloadSBOM } from '../services/api';

interface SBOMTabProps {
  analysisId: string;
  components: Component[];
}

type SortField = 'name' | 'version' | 'vulnerability_count' | 'risk_score';

export const SBOMTab: React.FC<SBOMTabProps> = ({ analysisId, components }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [ecosystemFilter, setEcosystemFilter] = useState('all');
  const [scopeFilter, setScopeFilter] = useState('all');
  const [vulnOnly, setVulnOnly] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [copiedPurl, setCopiedPurl] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('risk_score');
  const [sortAsc, setSortAsc] = useState(false);

  const directCount = components.filter(c => c.direct).length;
  const transitiveCount = components.length - directCount;
  const vulnerableCount = components.filter(c => c.vulnerability_count > 0).length;
  const cleanCount = components.length - vulnerableCount;
  const uniqueLicenses = new Set(components.map(c => c.license || 'Unknown')).size;

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false); // default descending for risk/vulns
    }
  };

  const filteredComponents = components
    .filter(c => {
      const term = searchTerm.toLowerCase();
      const matchesSearch = !term ||
        c.name.toLowerCase().includes(term) ||
        c.version.toLowerCase().includes(term) ||
        c.purl.toLowerCase().includes(term) ||
        (c.license && c.license.toLowerCase().includes(term));
      const matchesEco = ecosystemFilter === 'all' || c.ecosystem.toLowerCase() === ecosystemFilter.toLowerCase();
      const matchesScope = scopeFilter === 'all' || (scopeFilter === 'direct' ? c.direct : !c.direct);
      const matchesVuln = !vulnOnly || c.vulnerability_count > 0;
      return matchesSearch && matchesEco && matchesScope && matchesVuln;
    })
    .sort((a, b) => {
      let comparison = 0;
      if (sortField === 'name') {
        comparison = a.name.localeCompare(b.name);
      } else if (sortField === 'version') {
        comparison = a.version.localeCompare(b.version);
      } else if (sortField === 'vulnerability_count') {
        comparison = a.vulnerability_count - b.vulnerability_count;
      } else if (sortField === 'risk_score') {
        comparison = a.risk_score - b.risk_score;
      }
      return sortAsc ? comparison : -comparison;
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

  const copyPurl = (e: React.MouseEvent, purl: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(purl);
    setCopiedPurl(purl);
    setTimeout(() => setCopiedPurl(null), 2000);
  };

  const getLicenseColor = (license: string) => {
    const l = (license || '').toLowerCase();
    if (l.includes('mit') || l.includes('apache') || l.includes('bsd') || l.includes('isc')) {
      return 'bg-severity-low/15 text-severity-low border-severity-low/30';
    }
    if (l.includes('gpl') || l.includes('agpl') || l.includes('copyleft')) {
      return 'bg-severity-high/15 text-severity-high border-severity-high/30';
    }
    return 'bg-surface-elevated text-text-secondary border-surface-elevated';
  };

  return (
    <div className="space-y-6">
      {/* Action Header & Exports */}
      <div className="enterprise-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <Box className="w-5 h-5 text-accent-emerald" />
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
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-surface hover:bg-surface-elevated border border-surface-border text-text-primary text-xs font-mono font-medium transition-colors disabled:opacity-50 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-text-secondary" />
            <span>{exporting === 'cyclonedx' ? 'Exporting...' : 'CycloneDX 1.5 JSON'}</span>
          </button>

          <button
            onClick={() => handleExport('spdx')}
            disabled={exporting !== null}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-surface hover:bg-surface-elevated border border-surface-border text-text-primary text-xs font-mono font-medium transition-colors disabled:opacity-50 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-text-secondary" />
            <span>{exporting === 'spdx' ? 'Exporting...' : 'SPDX 2.3 JSON'}</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono text-xs">
        <div className="p-3 rounded-xl bg-surface border border-surface-elevated flex flex-col justify-between">
          <span className="text-[10px] text-text-secondary uppercase">Total Components</span>
          <span className="text-xl font-bold text-text-primary mt-1">{components.length}</span>
        </div>
        <div className="p-3 rounded-xl bg-surface border border-surface-elevated flex flex-col justify-between">
          <span className="text-[10px] text-text-secondary uppercase">Direct Dependencies</span>
          <span className="text-xl font-bold text-text-primary mt-1">{directCount}</span>
        </div>
        <div className="p-3 rounded-xl bg-surface border border-surface-elevated flex flex-col justify-between">
          <span className="text-[10px] text-text-secondary uppercase">Transitive Packages</span>
          <span className="text-xl font-bold text-text-secondary mt-1">{transitiveCount}</span>
        </div>
        <div className="p-3 rounded-xl bg-surface border border-surface-elevated flex flex-col justify-between">
          <span className="text-[10px] text-text-secondary uppercase">Vulnerable Packages</span>
          <span className="text-xl font-bold text-severity-critical mt-1">{vulnerableCount}</span>
        </div>
        <div className="p-3 rounded-xl bg-surface border border-surface-elevated flex flex-col justify-between">
          <span className="text-[10px] text-text-secondary uppercase">Clean Packages</span>
          <span className="text-xl font-bold text-severity-low mt-1">{cleanCount}</span>
        </div>
        <div className="p-3 rounded-xl bg-surface border border-surface-elevated flex flex-col justify-between">
          <span className="text-[10px] text-text-secondary uppercase">Unique Licenses</span>
          <span className="text-xl font-bold text-text-primary mt-1">{uniqueLicenses}</span>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="enterprise-card p-3 flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-text-secondary absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search package name, version, purl, or license..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-background-secondary border border-surface-border rounded-md pl-10 pr-4 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-emerald font-mono transition-colors"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <select
            value={ecosystemFilter}
            onChange={(e) => setEcosystemFilter(e.target.value)}
            className="bg-background-secondary border border-surface-border rounded-md px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-emerald font-mono cursor-pointer"
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
            className="bg-background-secondary border border-surface-border rounded-md px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-emerald font-mono cursor-pointer"
          >
            <option value="all">All Scopes</option>
            <option value="direct">Direct Only</option>
            <option value="transitive">Transitive Only</option>
          </select>

          <button
            onClick={() => setVulnOnly(!vulnOnly)}
            className={`px-3 py-2 rounded-xl text-xs font-mono font-bold transition-all border cursor-pointer whitespace-nowrap ${
              vulnOnly
                ? 'bg-severity-critical/20 text-severity-critical border-severity-critical'
                : 'bg-surface-elevated text-text-secondary hover:text-text-primary border-surface-elevated'
            }`}
          >
            Vulnerable ({vulnerableCount})
          </button>
        </div>
      </div>

      {/* Component Table */}
      <div className="enterprise-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-surface-elevated bg-surface-elevated/40 text-text-secondary font-mono uppercase text-[11px] tracking-wider select-none">
                <th className="py-3 px-4 cursor-pointer hover:text-text-primary" onClick={() => handleSort('name')}>
                  <div className="flex items-center space-x-1">
                    <span>Component</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4">Ecosystem</th>
                <th className="py-3 px-4 cursor-pointer hover:text-text-primary" onClick={() => handleSort('version')}>
                  <div className="flex items-center space-x-1">
                    <span>Installed Version</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4">Scope</th>
                <th className="py-3 px-4">License</th>
                <th className="py-3 px-4">Manifest Path</th>
                <th className="py-3 px-4 cursor-pointer hover:text-text-primary" onClick={() => handleSort('vulnerability_count')}>
                  <div className="flex items-center space-x-1">
                    <span>Vulnerabilities</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4 cursor-pointer hover:text-text-primary" onClick={() => handleSort('risk_score')}>
                  <div className="flex items-center space-x-1">
                    <span>Risk Score</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-elevated font-mono">
              {filteredComponents.map((c) => (
                <tr key={`${c.ecosystem}-${c.name}-${c.version}`} className="hover:bg-surface-elevated/40 transition-colors">
                  <td className="py-3 px-4">
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-text-primary">{c.name}</span>
                        <button
                          onClick={(e) => copyPurl(e, c.purl)}
                          className="text-text-secondary hover:text-accent-emerald transition-colors"
                          title="Copy Package URL (PURL)"
                        >
                          {copiedPurl === c.purl ? (
                            <Check className="w-3 h-3 text-severity-low" />
                          ) : (
                            <Copy className="w-3 h-3 opacity-60 hover:opacity-100" />
                          )}
                        </button>
                      </div>
                      <div className="text-[10px] text-text-secondary/70 truncate max-w-xs">{c.purl}</div>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded-md bg-surface-elevated text-text-secondary text-[11px] font-medium uppercase border border-surface-border">
                      {c.ecosystem}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-text-primary font-semibold">{c.version}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                      c.direct
                        ? 'bg-surface-elevated text-text-primary border border-surface-border'
                        : 'bg-surface-elevated text-text-secondary border border-surface-elevated'
                    }`}>
                      {c.direct ? 'Direct' : 'Transitive'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono border ${getLicenseColor(c.license)}`}>
                      {c.license || 'Unknown'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-text-secondary text-[11px] truncate max-w-[140px]" title={c.manifest_path}>
                    {c.manifest_path}
                  </td>
                  <td className="py-3 px-4">
                    {c.vulnerability_count > 0 ? (
                      <span className="px-2 py-0.5 rounded-md bg-severity-critical/20 text-severity-critical border border-severity-critical/30 font-bold">
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
                    No components found matching your search or filters.
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
