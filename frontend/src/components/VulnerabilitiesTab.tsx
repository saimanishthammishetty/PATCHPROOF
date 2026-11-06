import React, { useState } from 'react';
import type { VulnerabilityFinding } from '../types';
import {
  Bug, Search, ExternalLink, ShieldAlert, CheckCircle,
  HelpCircle, ChevronDown, ChevronRight, Zap, Target, Copy, Check, Filter, X
} from 'lucide-react';

interface VulnerabilitiesTabProps {
  vulnerabilities: VulnerabilityFinding[];
}

export const VulnerabilitiesTab: React.FC<VulnerabilitiesTabProps> = ({ vulnerabilities }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [ecosystemFilter, setEcosystemFilter] = useState('all');
  const [kevOnly, setKevOnly] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const countBySeverity = {
    all: vulnerabilities.length,
    critical: vulnerabilities.filter(v => v.severity.toUpperCase() === 'CRITICAL').length,
    high: vulnerabilities.filter(v => v.severity.toUpperCase() === 'HIGH').length,
    medium: vulnerabilities.filter(v => v.severity.toUpperCase() === 'MEDIUM').length,
    low: vulnerabilities.filter(v => v.severity.toUpperCase() === 'LOW').length,
  };

  const kevCount = vulnerabilities.filter(v => v.cisa_kev).length;

  const filteredVulns = vulnerabilities.filter(v => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = !term ||
      v.id.toLowerCase().includes(term) ||
      v.package.toLowerCase().includes(term) ||
      v.explanation.toLowerCase().includes(term) ||
      v.aliases.some(a => a.toLowerCase().includes(term));

    const matchesSeverity = severityFilter === 'all' || v.severity.toUpperCase() === severityFilter.toUpperCase();
    const matchesEco = ecosystemFilter === 'all' || v.ecosystem.toLowerCase() === ecosystemFilter.toLowerCase();
    const matchesKev = !kevOnly || v.cisa_kev;
    return matchesSearch && matchesSeverity && matchesEco && matchesKev;
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

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
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
    setKevOnly(false);
  };

  const hasActiveFilters = searchTerm !== '' || severityFilter !== 'all' || ecosystemFilter !== 'all' || kevOnly;

  return (
    <div className="space-y-6">
      {/* Title & Stats */}
      <div className="enterprise-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <Bug className="w-5 h-5 text-severity-critical" />
            Vulnerability Intelligence Feed
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Correlated advisory database powered by OSV.dev, GitHub Security Advisories, NVD, and CISA KEV.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1.5 rounded-md bg-surface-elevated text-text-secondary border border-surface-border font-semibold">
            {vulnerabilities.length} Total Findings
          </span>
          {kevCount > 0 && (
            <span className="px-3 py-1.5 rounded-xl bg-severity-critical/20 text-severity-critical border border-severity-critical/40 font-bold flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" />
              <span>{kevCount} KEV Weaponized</span>
            </span>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="enterprise-card p-4 space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-text-secondary absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by advisory ID (GHSA, CVE), package, or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-background-secondary border border-surface-border rounded-md pl-10 pr-9 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-emerald font-mono transition-colors"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2 w-full md:w-auto">
            <select
              value={ecosystemFilter}
              onChange={(e) => setEcosystemFilter(e.target.value)}
              className="bg-background-secondary border border-surface-border rounded-md px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-emerald font-mono w-full sm:w-auto cursor-pointer"
            >
              <option value="all">All Ecosystems</option>
              <option value="pypi">PyPI (Python)</option>
              <option value="npm">npm (JavaScript/TS)</option>
              <option value="golang">Go Modules</option>
              <option value="maven">Maven (Java)</option>
            </select>

            <button
              onClick={() => setKevOnly(!kevOnly)}
              className={`flex items-center space-x-1.5 px-3 py-2.5 rounded-xl border text-xs font-mono font-bold transition-all cursor-pointer whitespace-nowrap ${
                kevOnly
                  ? 'bg-severity-critical/20 border-severity-critical text-severity-critical shadow-sm'
                  : 'bg-surface-elevated border-surface-elevated text-text-secondary hover:text-text-primary'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>CISA KEV ({kevCount})</span>
            </button>

            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="p-2.5 rounded-xl bg-surface-elevated hover:bg-surface border border-surface-elevated text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
                title="Reset all filters"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Severity Filter Chips */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-surface-elevated/60 text-xs font-mono">
          <span className="text-[11px] text-text-secondary font-bold mr-1.5 uppercase">Severity:</span>
          {(['all', 'critical', 'high', 'medium', 'low'] as const).map(sev => {
            const count = countBySeverity[sev];
            const isActive = severityFilter === sev;
            return (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-3 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                  isActive
                    ? sev === 'critical'
                      ? 'bg-severity-critical text-white font-bold shadow-sm'
                      : sev === 'high'
                      ? 'bg-severity-high text-black font-bold shadow-sm'
                      : sev === 'medium'
                      ? 'bg-severity-medium text-black font-bold shadow-sm'
                      : 'bg-severity-low/20 text-severity-low border border-severity-low/40 font-bold'
                    : 'bg-surface-elevated/70 text-text-secondary hover:text-text-primary hover:bg-surface-elevated border border-surface-border'
                }`}
              >
                <span className="capitalize">{sev}</span> ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Findings List */}
      <div className="space-y-3.5">
        {filteredVulns.map((vuln) => {
          const isExpanded = expandedId === vuln.id;
          return (
            <div
              key={vuln.id}
              className="cyber-card rounded-2xl overflow-hidden shadow-lg transition-all"
            >
              {/* Card Summary Header */}
              <div
                onClick={() => toggleExpand(vuln.id)}
                className="p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 cursor-pointer select-none"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold font-mono text-text-primary">{vuln.id}</span>
                    <button
                      onClick={(e) => copyId(e, vuln.id)}
                      className="text-text-secondary hover:text-accent-emerald transition-colors"
                      title="Copy Advisory ID"
                    >
                      {copiedId === vuln.id ? (
                        <Check className="w-3.5 h-3.5 text-severity-low" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 opacity-60 hover:opacity-100" />
                      )}
                    </button>
                    {vuln.aliases.map(alias => (
                      <span key={alias} className="px-2 py-0.5 rounded-md bg-surface-elevated text-text-secondary text-[11px] font-mono border border-surface-elevated">
                        {alias}
                      </span>
                    ))}
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold font-mono border ${getSeverityBadge(vuln.severity)}`}>
                      {vuln.severity}
                    </span>
                    {vuln.cisa_kev && (
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-severity-critical text-white flex items-center gap-1 shadow-sm">
                        <Zap className="w-3 h-3" /> CISA KEV
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-surface-elevated text-text-secondary border border-surface-border">
                      CVSS: {vuln.cvss_score ? vuln.cvss_score.toFixed(1) : 'N/A'}
                    </span>
                    {vuln.epss_probability !== undefined && (
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-surface-elevated text-text-secondary border border-surface-elevated">
                        EPSS: {(vuln.epss_probability * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-text-secondary line-clamp-1 font-sans">{vuln.explanation}</p>
                </div>

                {/* Right Package & Reachability Pill */}
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
                  <div className="w-6 h-6 rounded-lg bg-surface-elevated flex items-center justify-center text-text-secondary">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </div>
                </div>
              </div>

              {/* Expanded Intelligence Drawer */}
              {isExpanded && (
                <div className="p-5 border-t border-surface-elevated bg-surface-elevated/40 space-y-4 text-xs font-mono">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-surface p-3.5 rounded-xl border border-surface-elevated space-y-1">
                      <span className="text-text-secondary uppercase text-[10px] font-bold tracking-wider">Affected Version Range</span>
                      <p className="text-text-primary font-bold">{vuln.affected_range || 'Direct affected release'}</p>
                    </div>

                    <div className="bg-surface p-3.5 rounded-xl border border-surface-elevated space-y-1">
                      <span className="text-text-secondary uppercase text-[10px] font-bold tracking-wider">Reachability Classification</span>
                      <p className="text-text-primary font-semibold flex items-center gap-1">
                        <Target className="w-3.5 h-3.5" />
                        {vuln.reachability === 'reachable' ? 'Direct Application Dependency (Reachable)' : 'Transitive / Deep Scope'}
                      </p>
                    </div>

                    <div className="bg-surface p-3.5 rounded-xl border border-surface-elevated space-y-1">
                      <span className="text-text-secondary uppercase text-[10px] font-bold tracking-wider">Evidence Confidence</span>
                      <p className="text-severity-low font-bold">{vuln.confidence}: {vuln.confidence_reason || 'Verified advisory record'}</p>
                    </div>
                  </div>

                  {/* Dependency Path if available */}
                  {vuln.dependency_path && vuln.dependency_path.length > 0 && (
                    <div className="bg-surface p-3.5 rounded-xl border border-surface-elevated space-y-1">
                      <span className="text-text-secondary uppercase text-[10px] font-bold tracking-wider">Dependency Graph Resolution Path:</span>
                      <div className="flex flex-wrap items-center gap-1.5 pt-1 text-text-primary">
                        {vuln.dependency_path.map((step, sIdx) => (
                          <React.Fragment key={sIdx}>
                            <span className="px-2 py-0.5 rounded bg-surface-elevated border border-surface-elevated font-semibold">
                              {step}
                            </span>
                            {sIdx < vuln.dependency_path.length - 1 && (
                              <span className="text-text-secondary">→</span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recommended Action */}
                  <div className="bg-surface p-4 rounded-md border border-surface-border space-y-1">
                    <span className="text-accent-amber font-semibold text-[11px] uppercase tracking-wider">Recommended Action:</span>
                    <p className="text-text-primary leading-relaxed font-sans">{vuln.recommended_action}</p>
                  </div>

                  {/* Advisory References */}
                  {vuln.source_links.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-text-secondary text-[11px] uppercase font-bold">Authoritative References:</span>
                      <div className="flex flex-wrap gap-2 pt-0.5">
                        {vuln.source_links.map((link, idx) => (
                          <a
                            key={idx}
                            href={link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-surface hover:bg-surface-elevated text-accent-emerald text-[11px] border border-surface-border transition-colors truncate max-w-md group"
                          >
                            <span className="truncate">{link}</span>
                            <ExternalLink className="w-3 h-3 shrink-0 group-hover:translate-x-0.5 transition-transform" />
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filteredVulns.length === 0 && (
          <div className="p-12 text-center text-text-secondary font-mono bg-surface rounded-2xl border border-surface-elevated">
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
    </div>
  );
};
