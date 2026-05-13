"use client";

import type { AgentResult } from "@/lib/api";

const agentLabels: Record<string, { label: string; color: string }> = {
  image_agent: { label: "Deepfake Detection", color: "#00d4ff" },
  video_agent: { label: "Liveness Check", color: "#7b2ff7" },
  voice_agent: { label: "Voice Analysis", color: "#4ade80" },
  behavior_agent: { label: "Behavior Check", color: "#fbbf24" },
};

const riskColors: Record<string, string> = {
  LOW: "#4ade80",
  MEDIUM: "#fbbf24",
  HIGH: "#f87171",
  CRITICAL: "#dc2626",
};

interface Props {
  name: string;
  result: AgentResult;
}

export default function AgentStatusCard({ name, result }: Props) {
  const info = agentLabels[name] || { label: name, color: "#999" };
  const riskColor = riskColors[result.risk_level] || "#999";
  const passed = result.score >= 60;

  return (
    <div className="glass rounded-xl p-4 group">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: info.color, opacity: 0.6 }}
          />
          <span className="text-[12px] font-medium text-white/60">{info.label}</span>
        </div>
        <span
          className="text-[10px] font-mono px-2 py-0.5 rounded"
          style={{ backgroundColor: `${riskColor}08`, color: riskColor, opacity: 0.7 }}
        >
          {result.risk_level}
        </span>
      </div>

      <div className="flex items-end gap-1.5 mb-3">
        <span
          className="text-xl font-bold font-mono"
          style={{ color: passed ? "#4ade80" : "#f87171", opacity: 0.8 }}
        >
          {Math.round(result.score)}
        </span>
        <span className="text-[10px] text-white/15 mb-0.5 font-mono">/100</span>
      </div>

      <div className="w-full h-1 bg-white/[0.03] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{
            width: `${result.score}%`,
            backgroundColor: passed ? "#4ade80" : "#f87171",
            opacity: 0.5,
          }}
        />
      </div>
    </div>
  );
}
