import React, { useState } from 'react';
import type { VulnerabilityFinding } from '../types';
import { 
  Bug, Search, ExternalLink, ShieldAlert, CheckCircle, 
  HelpCircle, ChevronDown, ChevronRight, Zap, Target
} from 'lucide-react';

interface VulnerabilitiesTabProps {
  vulnerabilities: VulnerabilityFinding[];
}

export const VulnerabilitiesTab: React.FC<VulnerabilitiesTabProps> = ({ vulnerabilities }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [kevOnly, setKevOnly] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filteredVulns = vulnerabilities.filter(v => {
    const matchesSearch = v.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          v.package.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          v.aliases.some(a => a.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesSeverity = severityFilter === 'all' || v.severity.toUpperCase() === severityFilter.toUpperCase();
    const matchesKev = !kevOnly || v.cisa_kev;
    return matchesSearch && matchesSeverity && matchesKev;
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

  return (
    <div className="space-y-6">
      {/* Title & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface border border-surface-elevated rounded-2xl p-5 shadow-xl">
        <div>
          <h2 className="text-lg font-bold text-text-primary font-mono tracking-tight flex items-center gap-2">
            <Bug className="w-5 h-5 text-severity-critical" />
            Vulnerability Intelligence Feed
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Correlated advisory database powered by OSV.dev, GitHub Security Advisories, NVD, and CISA KEV.
          </p>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono">
          <label className="flex items-center space-x-2 bg-surface-elevated px-3 py-2 rounded-xl border border-surface-elevated cursor-pointer hover:border-severity-critical/40 transition-colors">
            <input
              type="checkbox"
              checked={kevOnly}
              onChange={(e) => setKevOnly(e.target.checked)}
              className="rounded border-surface-elevated text-severity-critical focus:ring-0"
            />
            <span className="text-text-primary font-bold">CISA KEV Only</span>
          </label>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-surface/80 border border-surface-elevated p-3 rounded-xl">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search advisory ID, CVE, or affected package..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-surface-elevated border border-surface-elevated rounded-lg pl-9 pr-4 py-2 text-xs text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-brand-violet/50 font-mono"
          />
        </div>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-surface-elevated border border-surface-elevated rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-brand-violet/50 font-mono w-full sm:w-auto"
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Findings List */}
      <div className="space-y-4">
        {filteredVulns.map((vuln) => {
          const isExpanded = expandedId === vuln.id;
          return (
            <div
              key={vuln.id}
              className="bg-surface border border-surface-elevated rounded-2xl overflow-hidden shadow-lg transition-all hover:border-brand-violet/30"
            >
              {/* Card Summary Header */}
              <div
                onClick={() => toggleExpand(vuln.id)}
                className="p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 cursor-pointer select-none"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold font-mono text-text-primary">{vuln.id}</span>
                    {vuln.aliases.map(alias => (
                      <span key={alias} className="px-2 py-0.5 rounded bg-surface-elevated text-text-secondary text-[11px] font-mono">
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
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-elevated text-brand-cyan">
                      CVSS: {vuln.cvss_score?.toFixed(1) || 'N/A'}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-elevated text-text-secondary">
                      EPSS: {vuln.epss_probability ? `${(vuln.epss_probability * 100).toFixed(0)}%` : 'N/A'}
                    </span>
                  </div>

                  <p className="text-xs text-text-secondary line-clamp-1">{vuln.explanation}</p>
                </div>

                {/* Right Package & Reachability Pill */}
                <div className="flex items-center space-x-3 font-mono text-xs shrink-0">
                  <div className="text-right">
                    <div className="text-text-primary font-bold">{vuln.package}</div>
                    <div className="text-text-secondary text-[11px]">{vuln.affected_version} → <span className="text-severity-low font-bold">{vuln.fixed_version || 'Investigation required'}</span></div>
                  </div>
                  {isExpanded ? <ChevronDown className="w-4 h-4 text-text-secondary" /> : <ChevronRight className="w-4 h-4 text-text-secondary" />}
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
                      <p className="text-brand-cyan font-bold flex items-center gap-1">
                        <Target className="w-3.5 h-3.5" />
                        {vuln.reachability === 'reachable' ? 'Direct Application Dependency (Reachable)' : 'Transitive / Deep Scope'}
                      </p>
                    </div>

                    <div className="bg-surface p-3.5 rounded-xl border border-surface-elevated space-y-1">
                      <span className="text-text-secondary uppercase text-[10px] font-bold tracking-wider">Evidence Confidence</span>
                      <p className="text-severity-low font-bold">{vuln.confidence}: {vuln.confidence_reason || 'Verified advisory record'}</p>
                    </div>
                  </div>

                  {/* Recommended Action */}
                  <div className="bg-surface p-4 rounded-xl border border-brand-violet/30 space-y-1">
                    <span className="text-brand-violet font-bold text-[11px] uppercase tracking-wider">Recommended Action:</span>
                    <p className="text-text-primary">{vuln.recommended_action}</p>
                  </div>

                  {/* Advisory References */}
                  {vuln.source_links.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-text-secondary text-[11px] uppercase font-bold">Authoritative References:</span>
                      <div className="flex flex-wrap gap-2 pt-1">
                        {vuln.source_links.map((link, idx) => (
                          <a
                            key={idx}
                            href={link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center space-x-1 px-2.5 py-1 rounded bg-surface hover:bg-surface-elevated text-brand-cyan text-[11px] border border-surface-elevated transition-colors truncate max-w-sm"
                          >
                            <span>{link}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
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
            No vulnerabilities found matching your search or filters.
          </div>
        )}
      </div>
    </div>
  );
};
