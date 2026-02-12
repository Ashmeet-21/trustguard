"use client";

interface Props {
  score: number;
  decision: "PASS" | "REVIEW" | "FAIL";
}

export default function TrustScoreGauge({ score, decision }: Props) {
  const color =
    decision === "PASS"
      ? "#4ade80"
      : decision === "FAIL"
      ? "#f87171"
      : "#fbbf24";

  const circumference = 2 * Math.PI * 80;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width="200" height="200" className="transform -rotate-90">
        <circle
          cx="100"
          cy="100"
          r="80"
          fill="none"
          stroke="#1a1a1a"
          strokeWidth="12"
        />
        <circle
          cx="100"
          cy="100"
          r="80"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ marginTop: "60px" }}>
        <span className="text-4xl font-bold" style={{ color }}>
          {Math.round(score)}
        </span>
        <span className="text-sm text-[#666]">Trust Score</span>
      </div>
      <div
        className="mt-4 px-6 py-2 rounded-full text-sm font-semibold"
        style={{ backgroundColor: `${color}20`, color }}
      >
        {decision}
      </div>
    </div>
  );
}
