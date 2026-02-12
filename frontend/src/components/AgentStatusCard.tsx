"use client";

import type { AgentResult } from "@/lib/api";

const agentLabels: Record<string, { label: string; icon: string }> = {
  image_agent: { label: "Deepfake Detection", icon: "🖼️" },
  video_agent: { label: "Liveness Check", icon: "👤" },
  voice_agent: { label: "Voice Analysis", icon: "🎤" },
  behavior_agent: { label: "Behavior Check", icon: "⌨️" },
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
  const info = agentLabels[name] || { label: name, icon: "🔍" };
  const color = riskColors[result.risk_level] || "#999";
  const passed = result.score >= 60;

  return (
    <div className="bg-[#111] border border-[#222] rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{info.icon}</span>
          <span className="text-sm font-medium text-white">{info.label}</span>
        </div>
        <span
          className="text-xs px-2 py-1 rounded-md font-semibold"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {result.risk_level}
        </span>
      </div>

      <div className="flex items-end gap-2 mb-2">
        <span className="text-2xl font-bold" style={{ color: passed ? "#4ade80" : "#f87171" }}>
          {Math.round(result.score)}
        </span>
        <span className="text-xs text-[#666] mb-1">/100</span>
      </div>

      <div className="w-full h-2 bg-[#1a1a1a] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${result.score}%`,
            background: passed
              ? "linear-gradient(90deg, #22c55e, #4ade80)"
              : "linear-gradient(90deg, #dc2626, #f87171)",
          }}
        />
      </div>
    </div>
  );
}
