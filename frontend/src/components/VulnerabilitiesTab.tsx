import React, { useState } from 'react';
import type { VulnerabilityFinding, RemediationProposal, RiskOverview } from '../types';
import {
  Bug, Search, ExternalLink, ShieldAlert, CheckCircle,
  HelpCircle, ChevronDown, ChevronRight, Zap, Target, Copy, Check, Filter, X,
  FileCode, ArrowRight, ShieldCheck, Activity, Layers, AlertTriangle, Eye, Table as TableIcon, LayoutGrid
} from 'lucide-react';

interface VulnerabilitiesTabProps {
  vulnerabilities: VulnerabilityFinding[];
  remediations?: RemediationProposal[];
  onSelectTab?: (tab: string) => void;
  riskOverview?: RiskOverview;
}

export const VulnerabilitiesTab: React.FC<VulnerabilitiesTabProps> = ({
  vulnerabilities,
  remediations = [],
  onSelectTab,
  riskOverview
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [ecosystemFilter, setEcosystemFilter] = useState('all');
  const [cveFilter, setCveFilter] = useState<'all' | 'with_cve' | 'no_cve'>('all');
  const [scopeFilter, setScopeFilter] = useState('all');
  const [kevOnly, setKevOnly] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [selectedVuln, setSelectedVuln] = useState<VulnerabilityFinding | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showRiskModal, setShowRiskModal] = useState(false);

  const countBySeverity = {
    all: vulnerabilities.length,
    critical: vulnerabilities.filter(v => v.severity.toUpperCase() === 'CRITICAL').length,
    high: vulnerabilities.filter(v => v.severity.toUpperCase() === 'HIGH').length,
    medium: vulnerabilities.filter(v => v.severity.toUpperCase() === 'MEDIUM').length,
    low: vulnerabilities.filter(v => v.severity.toUpperCase() === 'LOW').length,
  };

  const kevCount = vulnerabilities.filter(v => v.cisa_kev).length;
  const withCveCount = vulnerabilities.filter(v => Boolean(v.cve_id)).length;
  const withoutCveCount = vulnerabilities.length - withCveCount;

  const filteredVulns = vulnerabilities.filter(v => {
    const term = searchTerm.toLowerCase();
    const cveStr = (v.cve_id || '').toLowerCase();
    const allCvesStr = (v.cve_ids || []).join(' ').toLowerCase();
    const matchesSearch = !term ||
      v.id.toLowerCase().includes(term) ||
      cveStr.includes(term) ||
      allCvesStr.includes(term) ||
      v.package.toLowerCase().includes(term) ||
      v.explanation.toLowerCase().includes(term) ||
      (v.description || '').toLowerCase().includes(term) ||
      v.aliases.some(a => a.toLowerCase().includes(term));

    const matchesSeverity = severityFilter === 'all' || v.severity.toUpperCase() === severityFilter.toUpperCase();
    const matchesEco = ecosystemFilter === 'all' || v.ecosystem.toLowerCase() === ecosystemFilter.toLowerCase();
    const matchesKev = !kevOnly || v.cisa_kev;
    const matchesCve = cveFilter === 'all' ||
      (cveFilter === 'with_cve' && Boolean(v.cve_id)) ||
      (cveFilter === 'no_cve' && !v.cve_id);
    const matchesScope = scopeFilter === 'all' || (v.scope || 'production').toLowerCase() === scopeFilter.toLowerCase();

    return matchesSearch && matchesSeverity && matchesEco && matchesKev && matchesCve && matchesScope;
  });

  const getSeverityBadge = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-severity-critical/20 text-severity-critical border-severity-critical/40';
      case 'HIGH':
        return 'bg-severity-high/20 text-severity-high border-severity-high/40';
      case 'MEDIUM':
        return 'bg-severity-medium/20 text-severity-medium border-severity-medium/40';
      default:
        return 'bg-severity-low/20 text-severity-low border-severity-low/40';
    }
  };

  const getScopeBadge = (scope?: string) => {
    const sc = (scope || 'production').toLowerCase();
    if (sc === 'production') {
      return 'bg-accent-emerald/15 text-accent-emerald border-accent-emerald/30';
    }
    if (sc === 'fixture') {
      return 'bg-severity-medium/15 text-severity-medium border-severity-medium/30';
    }
    if (sc === 'test') {
      return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
    }
    if (sc === 'development') {
      return 'bg-purple-500/15 text-purple-400 border-purple-500/30';
    }
    return 'bg-surface-elevated text-text-secondary border-surface-border';
  };

  const copyId = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSeverityFilter('all');
    setEcosystemFilter('all');
    setCveFilter('all');
    setScopeFilter('all');
    setKevOnly(false);
  };

  const hasActiveFilters = searchTerm !== '' || severityFilter !== 'all' || ecosystemFilter !== 'all' || cveFilter !== 'all' || scopeFilter !== 'all' || kevOnly;

  // Find matching remediation for a vulnerability
  const getMatchingRemediation = (vuln: VulnerabilityFinding): RemediationProposal | undefined => {
    return remediations.find(r =>
      r.package.toLowerCase() === vuln.package.toLowerCase() &&
      r.ecosystem.toLowerCase() === vuln.ecosystem.toLowerCase()
    );
  };

  return (
    <div className="space-y-6">
      {/* Title & Stats */}
      <div className="enterprise-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <Bug className="w-5 h-5 text-severity-critical" />
            CVE Intelligence & Vulnerability Evidence
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Correlated vulnerability database mapping official CVE identifiers, OSV advisories, and code declarations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <button
            onClick={() => setShowRiskModal(true)}
            className="px-3 py-1.5 rounded-md bg-surface-elevated hover:bg-surface border border-surface-border text-accent-emerald font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Inspect Risk Score Breakdown"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Score: {riskOverview ? `${riskOverview.score}/100` : 'Explain'}</span>
          </button>

          <span className="px-3 py-1.5 rounded-md bg-surface-elevated text-text-primary border border-surface-border font-semibold">
            {vulnerabilities.length} Findings ({withCveCount} CVEs)
          </span>

          {kevCount > 0 && (
            <span className="px-3 py-1.5 rounded-md bg-severity-critical/20 text-severity-critical border border-severity-critical/40 font-bold flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" />
              <span>{kevCount} KEV Weaponized</span>
            </span>
          )}

          {/* View toggle */}
          <div className="flex items-center rounded-md border border-surface-border bg-background-secondary p-0.5">
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded text-xs transition-colors cursor-pointer ${
                viewMode === 'table' ? 'bg-surface-elevated text-text-primary font-bold' : 'text-text-secondary hover:text-text-primary'
              }`}
              title="Table View (CVE Column)"
            >
              <TableIcon className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('cards')}
              className={`p-1.5 rounded text-xs transition-colors cursor-pointer ${
                viewMode === 'cards' ? 'bg-surface-elevated text-text-primary font-bold' : 'text-text-secondary hover:text-text-primary'
              }`}
              title="Card View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="enterprise-card p-4 space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-text-secondary absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by CVE ID (e.g. CVE-2018-18074), GHSA, package, or vulnerability details..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-background-secondary border border-surface-border rounded-md pl-10 pr-9 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-emerald font-mono transition-colors"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            {/* Ecosystem Filter */}
            <select
              value={ecosystemFilter}
              onChange={(e) => setEcosystemFilter(e.target.value)}
              className="bg-background-secondary border border-surface-border rounded-md px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-emerald font-mono cursor-pointer"
            >
              <option value="all">All Ecosystems</option>
              <option value="pypi">PyPI (Python)</option>
              <option value="npm">npm (JavaScript/TS)</option>
              <option value="golang">Go Modules</option>
              <option value="maven">Maven (Java)</option>
            </select>

            {/* CVE Assigned Filter */}
            <select
              value={cveFilter}
              onChange={(e) => setCveFilter(e.target.value as any)}
              className="bg-background-secondary border border-surface-border rounded-md px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-emerald font-mono cursor-pointer"
            >
              <option value="all">All Identifiers ({vulnerabilities.length})</option>
              <option value="with_cve">With CVE ID ({withCveCount})</option>
              <option value="no_cve">No CVE Assigned ({withoutCveCount})</option>
            </select>

            {/* Scope Filter */}
            <select
              value={scopeFilter}
              onChange={(e) => setScopeFilter(e.target.value)}
              className="bg-background-secondary border border-surface-border rounded-md px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-emerald font-mono cursor-pointer"
            >
              <option value="all">All Scopes</option>
              <option value="production">Production Only</option>
              <option value="fixture">Test Fixtures</option>
              <option value="test">Test Manifests</option>
              <option value="development">Dev Dependencies</option>
            </select>

            {/* KEV Filter Button */}
            <button
              onClick={() => setKevOnly(!kevOnly)}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-md border text-xs font-mono font-bold transition-all cursor-pointer whitespace-nowrap ${
                kevOnly
                  ? 'bg-severity-critical/20 border-severity-critical text-severity-critical shadow-sm'
                  : 'bg-surface-elevated border-surface-border text-text-secondary hover:text-text-primary'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>CISA KEV ({kevCount})</span>
            </button>

            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="p-2 rounded-md bg-surface-elevated hover:bg-surface border border-surface-border text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
                title="Reset all filters"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Severity Filter Chips */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-surface-border text-xs font-mono">
          <span className="text-[11px] text-text-secondary font-bold mr-1.5 uppercase">Severity:</span>
          {(['all', 'critical', 'high', 'medium', 'low'] as const).map(sev => {
            const count = countBySeverity[sev];
            const isActive = severityFilter === sev;
            return (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2.5 py-0.5 rounded text-xs font-mono transition-all cursor-pointer ${
                  isActive
                    ? sev === 'critical'
                      ? 'bg-severity-critical text-white font-bold shadow-sm'
                      : sev === 'high'
                      ? 'bg-severity-high text-black font-bold shadow-sm'
                      : sev === 'medium'
                      ? 'bg-severity-medium text-black font-bold shadow-sm'
                      : 'bg-severity-low/20 text-severity-low border border-severity-low/40 font-bold'
                    : 'bg-surface-elevated text-text-secondary hover:text-text-primary hover:bg-surface border border-surface-border'
                }`}
              >
                <span className="capitalize">{sev}</span> ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Table View */}
      {viewMode === 'table' ? (
        <div className="enterprise-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="bg-background-secondary border-b border-surface-border text-text-secondary text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4 font-semibold">CVE ID</th>
                  <th className="py-3 px-4 font-semibold">Advisory ID</th>
                  <th className="py-3 px-4 font-semibold">Package</th>
                  <th className="py-3 px-3 font-semibold">Installed</th>
                  <th className="py-3 px-3 font-semibold">Severity</th>
                  <th className="py-3 px-3 font-semibold">CVSS</th>
                  <th className="py-3 px-3 font-semibold">EPSS</th>
                  <th className="py-3 px-3 font-semibold">KEV</th>
                  <th className="py-3 px-4 font-semibold">Fixed Version</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filteredVulns.map((vuln) => {
                  const rem = getMatchingRemediation(vuln);
                  return (
                    <tr
                      key={vuln.id}
                      onClick={() => setSelectedVuln(vuln)}
                      className="hover:bg-surface-elevated/50 transition-colors cursor-pointer group"
                    >
                      {/* CVE ID Column */}
                      <td className="py-3 px-4 font-bold">
                        {vuln.cve_id ? (
                          <div className="flex items-center gap-1.5">
                            <span className="text-accent-emerald bg-accent-emerald/10 border border-accent-emerald/30 px-2 py-0.5 rounded text-xs font-mono font-bold">
                              {vuln.cve_id}
                            </span>
                            <button
                              onClick={(e) => copyId(e, vuln.cve_id!)}
                              className="text-text-secondary hover:text-accent-emerald opacity-60 hover:opacity-100 transition-opacity"
                              title="Copy CVE ID"
                            >
                              {copiedId === vuln.cve_id ? (
                                <Check className="w-3 h-3 text-severity-low" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                        ) : (
                          <span className="text-text-muted italic text-[11px]">
                            No CVE assigned
                          </span>
                        )}
                      </td>

                      {/* Advisory ID Column */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="text-text-primary font-semibold">{vuln.id}</span>
                          {vuln.aliases.length > 0 && (
                            <span className="text-[10px] text-text-secondary" title={vuln.aliases.join(', ')}>
                              (+{vuln.aliases.length})
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Package Column */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-text-primary">{vuln.package}</span>
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-surface-elevated text-text-secondary uppercase">
                            {vuln.ecosystem}
                          </span>
                          <span className={`px-1.5 py-0.2 rounded text-[9px] font-mono border ${getScopeBadge(vuln.scope)}`}>
                            {vuln.scope || 'production'}
                          </span>
                        </div>
                      </td>

                      {/* Installed Version */}
                      <td className="py-3 px-3 text-text-secondary font-mono">
                        {vuln.affected_version}
                      </td>

                      {/* Severity */}
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getSeverityBadge(vuln.severity)}`}>
                          {vuln.severity}
                        </span>
                      </td>

                      {/* CVSS */}
                      <td className="py-3 px-3 font-mono font-bold text-text-primary">
                        {vuln.cvss_score ? vuln.cvss_score.toFixed(1) : 'N/A'}
                      </td>

                      {/* EPSS */}
                      <td className="py-3 px-3 font-mono text-text-secondary">
                        {vuln.epss_probability !== undefined && vuln.epss_probability !== null ? `${(vuln.epss_probability * 100).toFixed(0)}%` : '—'}
                      </td>

                      {/* KEV */}
                      <td className="py-3 px-3">
                        {vuln.cisa_kev ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-severity-critical text-white flex items-center gap-1 w-fit shadow-sm">
                            <Zap className="w-3 h-3" /> KEV
                          </span>
                        ) : vuln.cisa_kev_status === 'unavailable' ? (
                          <span className="text-text-muted text-[10px] italic">Unavail</span>
                        ) : (
                          <span className="text-text-muted text-[11px]">—</span>
                        )}
                      </td>

                      {/* Fixed Version */}
                      <td className="py-3 px-4">
                        {vuln.fixed_version ? (
                          <span className="text-severity-low font-bold">
                            {vuln.fixed_version}
                          </span>
                        ) : (
                          <span className="text-text-muted italic text-[11px]">
                            Investigation required
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedVuln(vuln);
                            }}
                            className="px-2.5 py-1 rounded bg-surface border border-surface-border text-text-primary hover:bg-surface-elevated text-[11px] transition-colors flex items-center gap-1 cursor-pointer"
                          >
                            <Eye className="w-3 h-3" />
                            <span>Details</span>
                          </button>
                          {rem && onSelectTab && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectTab('remediation');
                              }}
                              className="px-2.5 py-1 rounded bg-accent-emerald/15 border border-accent-emerald/30 text-accent-emerald hover:bg-accent-emerald/25 text-[11px] font-bold transition-colors flex items-center gap-1 cursor-pointer"
                              title="Inspect Unified Diff Patch"
                            >
                              <span>Fix</span>
                              <ArrowRight className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filteredVulns.length === 0 && (
            <div className="p-12 text-center text-text-secondary font-mono">
              <p className="text-sm">No vulnerabilities found matching your search or filters.</p>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="mt-3 px-3 py-1.5 rounded-md bg-surface-elevated text-accent-emerald text-xs font-mono hover:bg-surface border border-surface-border transition-colors cursor-pointer"
                >
                  Clear all filters
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Cards View */
        <div className="space-y-3.5">
          {filteredVulns.map((vuln) => {
            const rem = getMatchingRemediation(vuln);
            return (
              <div
                key={vuln.id}
                onClick={() => setSelectedVuln(vuln)}
                className="enterprise-card p-5 hover:border-surface-border/80 transition-all cursor-pointer group space-y-3"
              >
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {vuln.cve_id ? (
                        <span className="text-sm font-bold font-mono text-accent-emerald bg-accent-emerald/10 border border-accent-emerald/30 px-2 py-0.5 rounded">
                          {vuln.cve_id}
                        </span>
                      ) : (
                        <span className="text-xs font-mono text-text-muted italic px-2 py-0.5 rounded bg-surface-elevated border border-surface-border">
                          No CVE assigned
                        </span>
                      )}

                      <span className="text-xs font-bold font-mono text-text-primary">{vuln.id}</span>

                      {vuln.aliases.map(alias => (
                        <span key={alias} className="px-2 py-0.5 rounded bg-surface-elevated text-text-secondary text-[11px] font-mono border border-surface-border">
                          {alias}
                        </span>
                      ))}

                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getSeverityBadge(vuln.severity)}`}>
                        {vuln.severity}
                      </span>

                      {vuln.cisa_kev && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-severity-critical text-white flex items-center gap-1 shadow-sm">
                          <Zap className="w-3 h-3" /> CISA KEV
                        </span>
                      )}

                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-elevated text-text-secondary border border-surface-border">
                        CVSS: {vuln.cvss_score ? vuln.cvss_score.toFixed(1) : 'N/A'}
                      </span>

                      {vuln.epss_probability !== undefined && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-elevated text-text-secondary border border-surface-border">
                          EPSS: {(vuln.epss_probability * 100).toFixed(0)}%
                        </span>
                      )}

                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${getScopeBadge(vuln.scope)}`}>
                        Scope: {vuln.scope || 'production'}
                      </span>
                    </div>

                    <p className="text-xs text-text-secondary font-sans leading-relaxed">{vuln.explanation}</p>
                  </div>

                  <div className="flex items-center space-x-3 font-mono text-xs shrink-0">
                    <div className="text-right">
                      <div className="text-text-primary font-bold flex items-center justify-end gap-1.5">
                        <span>{vuln.package}</span>
                        <span className="px-1.5 py-0.2 rounded text-[10px] bg-surface-elevated text-text-secondary uppercase">
                          {vuln.ecosystem}
                        </span>
                      </div>
                      <div className="text-text-secondary text-[11px]">
                        {vuln.affected_version} → <span className="text-severity-low font-bold">{vuln.fixed_version || 'Investigation required'}</span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-text-secondary group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </div>
            );
          })}

          {filteredVulns.length === 0 && (
            <div className="p-12 text-center text-text-secondary font-mono enterprise-card">
              <p className="text-sm">No vulnerabilities found matching your search or filters.</p>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="mt-3 px-3 py-1.5 rounded-md bg-surface-elevated text-accent-emerald text-xs font-mono hover:bg-surface border border-surface-border transition-colors cursor-pointer"
                >
                  Clear all filters
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Comprehensive Vulnerability Details Modal */}
      {selectedVuln && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div
            className="enterprise-card max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-surface-border space-y-5 p-6 animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-4 border-b border-surface-border">
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  {selectedVuln.cve_id ? (
                    <span className="text-base font-black font-mono text-accent-emerald bg-accent-emerald/10 border border-accent-emerald/30 px-2.5 py-0.5 rounded">
                      {selectedVuln.cve_id}
                    </span>
                  ) : (
                    <span className="text-xs font-mono text-text-muted italic px-2 py-0.5 rounded bg-surface-elevated border border-surface-border">
                      No CVE assigned
                    </span>
                  )}
                  <span className="text-sm font-bold font-mono text-text-primary">{selectedVuln.id}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getSeverityBadge(selectedVuln.severity)}`}>
                    {selectedVuln.severity}
                  </span>
                  {selectedVuln.cisa_kev && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-severity-critical text-white flex items-center gap-1 shadow-sm">
                      <Zap className="w-3 h-3" /> CISA KEV WEAPONIZED
                    </span>
                  )}
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${getScopeBadge(selectedVuln.scope)}`}>
                    Scope: {selectedVuln.scope || 'production'}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-text-primary font-sans leading-snug">
                  {selectedVuln.explanation}
                </h3>
              </div>

              <button
                onClick={() => setSelectedVuln(null)}
                className="p-1.5 rounded-md hover:bg-surface-elevated text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Evidence & Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono text-xs">
              <div className="p-3 rounded-md bg-background-secondary border border-surface-border">
                <span className="text-text-secondary uppercase text-[10px] font-semibold">CVSS v3 Base</span>
                <p className="text-text-primary font-bold text-sm mt-0.5">
                  {selectedVuln.cvss_score ? `${selectedVuln.cvss_score.toFixed(1)} / 10` : 'Not evaluated'}
                </p>
              </div>

              <div className="p-3 rounded-md bg-background-secondary border border-surface-border">
                <span className="text-text-secondary uppercase text-[10px] font-semibold">EPSS Probability</span>
                <p className="text-text-primary font-bold text-sm mt-0.5">
                  {selectedVuln.epss_probability !== undefined && selectedVuln.epss_probability !== null ? `${(selectedVuln.epss_probability * 100).toFixed(1)}%` : 'Unavailable'}
                </p>
                {selectedVuln.epss_percentile !== undefined && selectedVuln.epss_percentile !== null && (
                  <p className="text-[10px] text-text-secondary mt-0.5 truncate">
                    {Math.round(selectedVuln.epss_percentile * 100)}th %ile ({selectedVuln.epss_source || 'FIRST'})
                  </p>
                )}
              </div>

              <div className="p-3 rounded-md bg-background-secondary border border-surface-border">
                <span className="text-text-secondary uppercase text-[10px] font-semibold">CISA KEV Status</span>
                <p className={`font-bold text-xs mt-0.5 ${selectedVuln.cisa_kev ? 'text-severity-critical' : 'text-text-primary'}`}>
                  {selectedVuln.cisa_kev ? 'Weaponized' : (selectedVuln.cisa_kev_status === 'unavailable' ? 'Unavailable' : 'Not Listed')}
                </p>
                {selectedVuln.cisa_kev_date_added && (
                  <p className="text-[10px] text-text-secondary mt-0.5 truncate">
                    Added: {selectedVuln.cisa_kev_date_added}
                  </p>
                )}
              </div>

              <div className="p-3 rounded-md bg-background-secondary border border-surface-border">
                <span className="text-text-secondary uppercase text-[10px] font-semibold">Affected Range</span>
                <p className="text-text-primary font-bold text-xs mt-0.5 truncate">
                  {selectedVuln.affected_range || selectedVuln.affected_version}
                </p>
              </div>

              <div className="p-3 rounded-md bg-background-secondary border border-surface-border">
                <span className="text-text-secondary uppercase text-[10px] font-semibold">Recommended Fix</span>
                <p className="text-severity-low font-bold text-xs mt-0.5 truncate">
                  {selectedVuln.fixed_version || 'Investigation required'}
                </p>
              </div>
            </div>

            {/* Detailed Description */}
            {selectedVuln.description && selectedVuln.description !== selectedVuln.explanation && (
              <div className="space-y-1.5 font-mono text-xs">
                <span className="text-text-secondary uppercase text-[10px] font-semibold tracking-wider">Technical Advisory Description:</span>
                <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border text-text-primary text-xs leading-relaxed font-sans max-h-40 overflow-y-auto">
                  {selectedVuln.description}
                </div>
              </div>
            )}

            {/* Repository Location Evidence & Code Snippet */}
            <div className="space-y-2 font-mono text-xs">
              <span className="text-text-secondary uppercase text-[10px] font-semibold tracking-wider flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-accent-emerald" />
                Repository Code Declaration & Provenance
              </span>

              <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                  <span className="text-text-secondary">
                    File: <code className="text-text-primary font-bold">{selectedVuln.manifest_path || selectedVuln.dependency_path?.[0] || 'Unknown'}</code>
                  </span>
                  {selectedVuln.manifest_line && (
                    <span className="text-accent-emerald font-bold">
                      Line: {selectedVuln.manifest_line}
                    </span>
                  )}
                </div>

                {selectedVuln.manifest_snippet && (
                  <div className="p-2.5 rounded bg-background border border-surface-border/60 text-text-primary font-mono text-xs">
                    <span className="text-text-secondary select-none mr-2 font-bold">{selectedVuln.manifest_line || 1} |</span>
                    <span className="text-severity-critical font-bold">{selectedVuln.manifest_snippet}</span>
                  </div>
                )}

                <div className="text-[11px] text-text-secondary pt-1 flex items-center gap-2">
                  <Target className="w-3 h-3 text-text-secondary" />
                  <span>Reachability: <strong className="text-text-primary">
                    {selectedVuln.reachability === 'runtime_reachable' ? 'Runtime Reachable (Call Graph Verified)' :
                     selectedVuln.reachability === 'direct_dependency' ? 'Direct Dependency (Runtime Unverified)' :
                     selectedVuln.reachability === 'reachable' ? 'Direct Application Dependency' :
                     selectedVuln.reachability === 'transitive_dependency' ? 'Transitive Dependency' :
                     'Runtime Reachability Unverified'}
                  </strong></span>
                  <span>•</span>
                  <span>Scope: <strong className="text-text-primary">{selectedVuln.scope || 'production'}</strong> ({selectedVuln.scope_reason || 'Verified manifest'})</span>
                </div>
              </div>
            </div>

            {/* Remediation & Unified Diff Section */}
            {(() => {
              const matchingRem = getMatchingRemediation(selectedVuln);
              return (
                <div className="space-y-2 font-mono text-xs">
                  <span className="text-accent-emerald uppercase text-[10px] font-semibold tracking-wider flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Automated Safe Remediation Plan
                  </span>

                  {matchingRem ? (
                    <div className="p-3.5 rounded-md bg-background-secondary border border-accent-emerald/30 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-text-primary font-bold">
                            Upgrade <code className="text-severity-critical">{matchingRem.current_version}</code> → <code className="text-severity-low">{matchingRem.proposed_version}</code>
                          </p>
                          <p className="text-[11px] text-text-secondary mt-0.5">{matchingRem.reason}</p>
                        </div>

                        {onSelectTab && (
                          <button
                            onClick={() => {
                              setSelectedVuln(null);
                              onSelectTab('remediation');
                            }}
                            className="px-3 py-1.5 rounded-md bg-accent-emerald text-white text-xs font-bold font-mono hover:bg-accent-emerald-hover transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
                          >
                            <span>Inspect Unified Diff</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      {matchingRem.diff && (
                        <div className="p-2.5 rounded bg-background border border-surface-border text-xs font-mono overflow-x-auto max-h-32">
                          <pre className="text-text-secondary leading-relaxed">
                            {matchingRem.diff.split('\n').map((line, idx) => (
                              <div
                                key={idx}
                                className={
                                  line.startsWith('+') && !line.startsWith('+++')
                                    ? 'text-severity-low font-bold bg-severity-low/10 px-1'
                                    : line.startsWith('-') && !line.startsWith('---')
                                    ? 'text-severity-critical font-bold bg-severity-critical/10 px-1'
                                    : ''
                                }
                              >
                                {line}
                              </div>
                            ))}
                          </pre>
                        </div>
                      )}

                      <div className="p-2 rounded bg-surface border border-surface-border/50 text-[11px] text-text-secondary flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-accent-emerald shrink-0" />
                        <span>PATCHPROOF Safety Rule: Proposes verified non-breaking version with human-in-the-loop authorization. Global <code>NEVER_MERGE</code> guard active.</span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border space-y-1">
                      <p className="text-text-primary font-semibold">{selectedVuln.recommended_action}</p>
                      <p className="text-[11px] text-text-secondary">
                        {selectedVuln.fixed_version
                          ? `Vendor advisory recommends upgrading to >= ${selectedVuln.fixed_version}.`
                          : 'No upstream fixed release is currently declared in the OSV advisory.'}
                      </p>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Authoritative References */}
            {selectedVuln.source_links.length > 0 && (
              <div className="space-y-1.5 font-mono text-xs">
                <span className="text-text-secondary uppercase text-[10px] font-semibold tracking-wider">Authoritative Advisory References:</span>
                <div className="flex flex-wrap gap-2 pt-0.5">
                  {selectedVuln.source_links.map((link, idx) => (
                    <a
                      key={idx}
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-background-secondary hover:bg-surface-elevated text-accent-emerald text-[11px] border border-surface-border transition-colors truncate max-w-md group"
                    >
                      <span className="truncate">{link}</span>
                      <ExternalLink className="w-3 h-3 shrink-0 group-hover:translate-x-0.5 transition-transform" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Close Button Footer */}
            <div className="pt-3 border-t border-surface-border flex justify-end">
              <button
                onClick={() => setSelectedVuln(null)}
                className="px-4 py-2 rounded-md bg-surface-elevated hover:bg-surface border border-surface-border text-text-primary text-xs font-mono font-semibold transition-colors cursor-pointer"
              >
                Close Finding Details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Explainable Risk Modal */}
      {showRiskModal && riskOverview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div
            className="enterprise-card max-w-2xl w-full shadow-2xl border border-surface-border space-y-5 p-6 animate-scale-up font-mono"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <h3 className="text-base font-bold text-text-primary flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent-emerald" />
                Explainable Risk Engine Audit Breakdown
              </h3>
              <button
                onClick={() => setShowRiskModal(false)}
                className="p-1 rounded-md text-text-secondary hover:text-text-primary cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border">
                <span className="text-text-secondary text-[10px] uppercase font-semibold">Total Repository Risk</span>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-black text-text-primary">{riskOverview.score}</span>
                  <span className="text-xs text-text-secondary">/100</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ml-auto ${getSeverityBadge(riskOverview.label)}`}>
                    {riskOverview.label}
                  </span>
                </div>
                <p className="text-[11px] text-text-secondary mt-1">Includes test fixtures, tooling, and demo assets.</p>
              </div>

              <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border">
                <span className="text-text-secondary text-[10px] uppercase font-semibold">Production-Scoped Risk</span>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-black text-accent-emerald">{riskOverview.production_score ?? 0.0}</span>
                  <span className="text-xs text-text-secondary">/100</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ml-auto ${getSeverityBadge(riskOverview.production_label || 'Low')}`}>
                    {riskOverview.production_label || 'Low'}
                  </span>
                </div>
                <p className="text-[11px] text-text-secondary mt-1">Evaluates only production runtime manifests.</p>
              </div>
            </div>

            {/* Findings Contribution Breakdown */}
            <div className="space-y-2 text-xs">
              <span className="text-text-secondary uppercase text-[10px] font-semibold">Finding Statistics:</span>
              <div className="p-3.5 rounded-md bg-background-secondary border border-surface-border space-y-2">
                <div className="flex justify-between py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">Total Vulnerability Findings:</span>
                  <span className="text-text-primary font-bold">{vulnerabilities.length}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">Severity (Crit / High / Med / Low):</span>
                  <span className="text-text-primary font-bold">
                    {countBySeverity.critical} / {countBySeverity.high} / {countBySeverity.medium} / {countBySeverity.low}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">Findings with Official CVE IDs:</span>
                  <span className="text-accent-emerald font-bold">{withCveCount}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">Findings without Assigned CVE:</span>
                  <span className="text-text-secondary font-bold">{withoutCveCount}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border/50">
                  <span className="text-text-secondary">CISA KEV Weaponized Overrides:</span>
                  <span className={kevCount > 0 ? 'text-severity-critical font-bold' : 'text-text-secondary'}>
                    {kevCount}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-text-secondary">Scope Breakdown (Prod / Fixture / Test / Dev):</span>
                  <span className="text-text-primary font-bold">
                    {vulnerabilities.filter(v => (v.scope || 'production') === 'production').length} / {vulnerabilities.filter(v => v.scope === 'fixture').length} / {vulnerabilities.filter(v => v.scope === 'test').length} / {vulnerabilities.filter(v => v.scope === 'development').length}
                  </span>
                </div>
              </div>
            </div>

            <p className="text-[11px] text-text-secondary leading-relaxed">
              {riskOverview.summary_explanation}
            </p>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowRiskModal(false)}
                className="px-4 py-2 rounded-md bg-surface-elevated hover:bg-surface border border-surface-border text-text-primary text-xs font-semibold cursor-pointer"
              >
                Close Audit View
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
