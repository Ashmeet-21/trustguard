"use client";

import { useEffect, useState } from "react";
import { getAnalyticsSummary, getRecentActivity } from "@/lib/api";

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

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAnalyticsSummary(), getRecentActivity(20)])
      .then(([s, a]) => {
        setSummary(s);
        setActivity(a || []);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-16 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-[#333] border-t-[#7b2ff7] rounded-full mx-auto mb-4" />
        <p className="text-[#666] text-sm">Loading analytics...</p>
      </div>
    );
  }

  const riskColors: Record<string, string> = {
    LOW: "#4ade80",
    MEDIUM: "#fbbf24",
    HIGH: "#f87171",
    CRITICAL: "#dc2626",
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <h1 className="text-3xl font-bold mb-2 gradient-text">Dashboard</h1>
      <p className="text-[#666] text-sm mb-8">Platform analytics and recent verification activity</p>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Total Scans", value: summary?.total_verifications ?? 0, color: "#00d4ff" },
          { label: "Deepfakes Caught", value: summary?.deepfakes_caught ?? 0, color: "#f87171" },
          { label: "Clean Results", value: summary?.clean_results ?? 0, color: "#4ade80" },
          {
            label: "Avg Processing",
            value: `${Math.round(summary?.avg_processing_time_ms ?? 0)}ms`,
            color: "#fbbf24",
          },
        ].map((card, i) => (
          <div key={i} className="bg-[#111] border border-[#222] rounded-xl p-5">
            <div className="text-xs text-[#555] uppercase tracking-wider mb-1">{card.label}</div>
            <div className="text-2xl font-bold" style={{ color: card.color }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid md:grid-cols-2 gap-4 mb-8">
        {/* By Type */}
        <div className="bg-[#111] border border-[#222] rounded-xl p-5">
          <h3 className="text-sm font-medium text-[#999] mb-4 uppercase tracking-wider">
            Scans by Type
          </h3>
          {summary?.by_type && Object.entries(summary.by_type).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(summary.by_type).map(([type, count]) => {
                const total = summary.total_verifications || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={type}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-[#ccc]">{type.replace(/_/g, " ")}</span>
                      <span className="text-[#888]">{count} ({pct}%)</span>
                    </div>
                    <div className="w-full h-2 bg-[#1a1a1a] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full gradient-bg transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-[#555] text-sm">No data yet</p>
          )}
        </div>

        {/* By Risk */}
        <div className="bg-[#111] border border-[#222] rounded-xl p-5">
          <h3 className="text-sm font-medium text-[#999] mb-4 uppercase tracking-wider">
            Risk Distribution
          </h3>
          {summary?.by_risk_level && Object.entries(summary.by_risk_level).length > 0 ? (
            <div className="space-y-3">
              {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((level) => {
                const count = summary.by_risk_level[level] || 0;
                const total = summary.total_verifications || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={level}>
                    <div className="flex justify-between text-xs mb-1">
                      <span style={{ color: riskColors[level] }}>{level}</span>
                      <span className="text-[#888]">{count}</span>
                    </div>
                    <div className="w-full h-2 bg-[#1a1a1a] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: riskColors[level],
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-[#555] text-sm">No data yet</p>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-[#111] border border-[#222] rounded-xl p-5">
        <h3 className="text-sm font-medium text-[#999] mb-4 uppercase tracking-wider">
          Recent Activity
        </h3>
        {activity.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#666] text-xs uppercase tracking-wider border-b border-[#222]">
                  <th className="text-left py-2 pr-4">Type</th>
                  <th className="text-left py-2 pr-4">File</th>
                  <th className="text-left py-2 pr-4">Result</th>
                  <th className="text-left py-2 pr-4">Risk</th>
                  <th className="text-right py-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {activity.map((item) => (
                  <tr key={item.id} className="border-b border-[#1a1a1a] hover:bg-[#1a1a1a]/50 transition">
                    <td className="py-2.5 pr-4 text-[#ccc]">{item.type?.replace(/_/g, " ") || "—"}</td>
                    <td className="py-2.5 pr-4 text-[#888] max-w-[150px] truncate">
                      {item.filename || "—"}
                    </td>
                    <td className="py-2.5 pr-4">
                      {item.is_deepfake !== null && item.is_deepfake !== undefined ? (
                        <span className={item.is_deepfake ? "text-[#f87171]" : "text-[#4ade80]"}>
                          {item.is_deepfake ? "FLAGGED" : "CLEAN"}
                        </span>
                      ) : (
                        <span className="text-[#555]">—</span>
                      )}
                    </td>
                    <td className="py-2.5 pr-4">
                      {item.risk_level ? (
                        <span
                          className="text-xs px-2 py-0.5 rounded"
                          style={{
                            backgroundColor: `${riskColors[item.risk_level] || "#999"}20`,
                            color: riskColors[item.risk_level] || "#999",
                          }}
                        >
                          {item.risk_level}
                        </span>
                      ) : (
                        <span className="text-[#555]">—</span>
                      )}
                    </td>
                    <td className="py-2.5 text-right text-[#666]">
                      {item.processing_time_ms ? `${Math.round(item.processing_time_ms)}ms` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-[#555] text-sm text-center py-8">
            No verification activity yet. Run a verification to see data here.
          </p>
        )}
      </div>
    </div>
  );
}
