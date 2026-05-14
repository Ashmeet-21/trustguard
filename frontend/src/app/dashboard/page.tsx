"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAnalyticsSummary, getRecentActivity } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import Link from "next/link";

interface Summary {
  total_verifications: number;
  deepfakes_caught: number;
  clean_results: number;
  avg_confidence: number;
  avg_processing_time_ms: number;
  by_type: Record<string, number>;
  by_risk_level: Record<string, number>;
}

interface ActivityItem {
  id: number;
  type: string;
  filename?: string;
  is_deepfake?: boolean;
  confidence?: number;
  risk_level?: string;
  processing_time_ms?: number;
  created_at?: string;
}

const riskColors: Record<string, string> = {
  LOW: "#4ade80",
  MEDIUM: "#fbbf24",
  HIGH: "#f87171",
  CRITICAL: "#dc2626",
};

const riskExplanations: Record<string, string> = {
  LOW: "High confidence the input is authentic. All checks passed cleanly.",
  MEDIUM: "Some minor concerns detected. May need additional verification.",
  HIGH: "Significant red flags found. Likely fake or manipulated content.",
  CRITICAL: "Strong indicators of deepfake, spoof, or bot activity detected.",
};

const typeLabels: Record<string, string> = {
  deepfake_image: "Deepfake (Image)",
  deepfake_video: "Deepfake (Video)",
  liveness_image: "Liveness (Image)",
  liveness_video: "Liveness (Video)",
  voice_detection: "Voice Analysis",
  behavior_analysis: "Behavioral Check",
  kyc: "Full KYC",
  batch: "Batch Scan",
};

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRisk, setExpandedRisk] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    if (!user) return;
    Promise.all([getAnalyticsSummary(), getRecentActivity(20)])
      .then(([s, a]) => {
        setSummary(s);
        setActivity(a || []);
      })
      .finally(() => setLoading(false));
  }, [user]);

  if (authLoading || !user || loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-20 text-center">
        <div className="spinner w-10 h-10 mx-auto mb-4" />
        <p className="text-white/25 text-sm">Loading analytics...</p>
      </div>
    );
  }

  const hasData = summary && summary.total_verifications > 0;
  const catchRate = hasData && summary.total_verifications > 0
    ? Math.round((summary.deepfakes_caught / summary.total_verifications) * 100)
    : 0;

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="flex items-end justify-between mb-10 fade-up">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-white/20 mb-2">Analytics</p>
          <h1 className="text-3xl md:text-4xl font-bold text-white/90 tracking-tight">Dashboard</h1>
          <p className="text-white/25 text-sm mt-1.5">
            Real-time metrics from all verification scans
          </p>
        </div>
        <Link
          href="/verify"
          className="btn-glow text-white px-5 py-2.5 rounded-xl text-sm font-medium hidden md:block"
        >
          New Verification
        </Link>
      </div>

      {!hasData ? (
        /* Empty state */
        <div className="glass rounded-2xl p-14 text-center mb-8 fade-up stagger-1">
          <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mx-auto mb-5">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/20">
              <path d="M18 20V10M12 20V4M6 20v-6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h2 className="text-base font-semibold text-white/70 mb-2">No Verification Data Yet</h2>
          <p className="text-sm text-white/25 mb-8 max-w-md mx-auto">
            Run your first verification to see analytics here. Every scan gets tracked with
            its result, risk level, and processing time.
          </p>
          <Link
            href="/verify"
            className="btn-glow text-white px-6 py-2.5 rounded-xl text-sm font-medium inline-block"
          >
            Run First Verification
          </Link>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            {[
              {
                label: "Total Scans",
                value: summary.total_verifications,
                sub: "All-time requests",
                color: "#00d4ff",
              },
              {
                label: "Flagged",
                value: summary.deepfakes_caught,
                sub: `${catchRate}% catch rate`,
                color: "#f87171",
              },
              {
                label: "Clean",
                value: summary.clean_results,
                sub: "Verified authentic",
                color: "#4ade80",
              },
              {
                label: "Avg Speed",
                value: `${Math.round(summary.avg_processing_time_ms)}ms`,
                sub: "Per verification",
                color: "#fbbf24",
              },
            ].map((card, i) => (
              <div key={i} className={`glass rounded-2xl p-5 fade-up stagger-${i + 1}`}>
                <p className="text-[10px] uppercase tracking-[0.15em] text-white/15 mb-3">{card.label}</p>
                <div className="text-2xl font-bold font-mono" style={{ color: card.color, opacity: 0.8 }}>
                  {card.value}
                </div>
                <p className="text-[11px] text-white/15 mt-1">{card.sub}</p>
              </div>
            ))}
          </div>

          {/* Charts Row */}
          <div className="grid md:grid-cols-2 gap-3 mb-8">
            {/* By Type */}
            <div className="glass rounded-2xl p-6 fade-up stagger-5">
              <p className="text-[10px] uppercase tracking-[0.15em] text-white/15 mb-1">Scans by Type</p>
              <p className="text-[11px] text-white/10 mb-5">Which detection agents were used</p>
              {summary.by_type && Object.entries(summary.by_type).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(summary.by_type).map(([type, count]) => {
                    const total = summary.total_verifications || 1;
                    const pct = Math.round((count / total) * 100);
                    const label = typeLabels[type] || type.replace(/_/g, " ");
                    return (
                      <div key={type}>
                        <div className="flex justify-between text-[11px] mb-1.5">
                          <span className="text-white/40">{label}</span>
                          <span className="text-white/15 font-mono">{count} ({pct}%)</span>
                        </div>
                        <div className="w-full h-1 bg-white/[0.03] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-1000 ease-out"
                            style={{
                              width: `${Math.max(pct, 2)}%`,
                              background: 'linear-gradient(90deg, #00d4ff, #7b2ff7)',
                              opacity: 0.6,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-white/15 text-sm">No data yet</p>
              )}
            </div>

            {/* By Risk */}
            <div className="glass rounded-2xl p-6 fade-up stagger-6">
              <p className="text-[10px] uppercase tracking-[0.15em] text-white/15 mb-1">Risk Distribution</p>
              <p className="text-[11px] text-white/10 mb-5">Click a level for details</p>
              {summary.by_risk_level && Object.entries(summary.by_risk_level).length > 0 ? (
                <div className="space-y-4">
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((level) => {
                    const count = summary.by_risk_level[level] || 0;
                    const total = summary.total_verifications || 1;
                    const pct = Math.round((count / total) * 100);
                    const isExpanded = expandedRisk === level;
                    const color = riskColors[level];
                    return (
                      <div key={level}>
                        <button
                          onClick={() => setExpandedRisk(isExpanded ? null : level)}
                          className="w-full text-left group"
                        >
                          <div className="flex justify-between text-[11px] mb-1.5">
                            <span
                              className="font-medium group-hover:opacity-100 transition-opacity"
                              style={{ color, opacity: 0.6 }}
                            >
                              {level}
                              <span className="text-white/10 ml-1">{isExpanded ? "−" : "+"}</span>
                            </span>
                            <span className="text-white/15 font-mono">{count} ({pct}%)</span>
                          </div>
                        </button>
                        <div className="w-full h-1 bg-white/[0.03] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-1000 ease-out"
                            style={{
                              width: `${Math.max(pct, 2)}%`,
                              backgroundColor: color,
                              opacity: 0.5,
                            }}
                          />
                        </div>
                        {isExpanded && (
                          <p
                            className="text-[11px] text-white/20 mt-2 pl-3 border-l"
                            style={{ borderColor: `${color}30` }}
                          >
                            {riskExplanations[level]}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-white/15 text-sm">No data yet</p>
              )}
            </div>
          </div>
        </>
      )}

      {/* Recent Activity */}
      <div className="glass rounded-2xl p-6 fade-up stagger-7">
        <div className="flex items-center justify-between mb-5">
          <div>
            <p className="text-[10px] uppercase tracking-[0.15em] text-white/15 mb-0.5">Recent Activity</p>
            <p className="text-[11px] text-white/10">
              Last {activity.length} results — newest first
            </p>
          </div>
        </div>

        {activity.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] text-white/15 uppercase tracking-wider border-b border-white/[0.04]">
                  <th className="text-left py-2.5 pr-4 font-medium">Type</th>
                  <th className="text-left py-2.5 pr-4 font-medium">File</th>
                  <th className="text-left py-2.5 pr-4 font-medium">Result</th>
                  <th className="text-left py-2.5 pr-4 font-medium">Risk</th>
                  <th className="text-right py-2.5 font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {activity.map((item) => {
                  const typeLabel = typeLabels[item.type] || item.type?.replace(/_/g, " ") || "—";
                  return (
                    <tr
                      key={item.id}
                      className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors duration-200"
                    >
                      <td className="py-3 pr-4 text-white/40 text-[12px]">{typeLabel}</td>
                      <td className="py-3 pr-4 text-white/20 max-w-[150px] truncate text-[12px] font-mono">
                        {item.filename || "—"}
                      </td>
                      <td className="py-3 pr-4">
                        {item.is_deepfake !== null && item.is_deepfake !== undefined ? (
                          <span
                            className="text-[11px] font-medium"
                            style={{ color: item.is_deepfake ? "#f87171" : "#4ade80", opacity: 0.7 }}
                          >
                            {["liveness_image", "liveness_video"].includes(item.type)
                              ? item.is_deepfake ? "SPOOF" : "LIVE"
                              : item.is_deepfake ? "FLAGGED" : "CLEAN"}
                          </span>
                        ) : (
                          <span className="text-white/10">—</span>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        {item.risk_level ? (
                          <span
                            className="text-[10px] font-mono px-2 py-0.5 rounded"
                            style={{
                              backgroundColor: `${riskColors[item.risk_level] || "#999"}08`,
                              color: riskColors[item.risk_level] || "#999",
                              opacity: 0.7,
                            }}
                          >
                            {item.risk_level}
                          </span>
                        ) : (
                          <span className="text-white/10">—</span>
                        )}
                      </td>
                      <td className="py-3 text-right text-white/15 text-[12px] font-mono">
                        {item.processing_time_ms
                          ? `${Math.round(item.processing_time_ms)}ms`
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-white/20 text-sm mb-1">No verification activity yet.</p>
            <p className="text-[11px] text-white/10">
              Each scan gets logged here with its result, risk level, and processing time.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
