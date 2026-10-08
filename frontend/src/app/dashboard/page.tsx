"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getAnalyticsSummary, getRecentActivity } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";

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

const RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

const RISK_STYLE: Record<string, { word: string; color: string; meaning: string }> = {
  LOW: { word: "Low", color: "var(--color-pass)", meaning: "Every check passed cleanly" },
  MEDIUM: { word: "Medium", color: "var(--color-review)", meaning: "Minor concerns, may need another look" },
  HIGH: { word: "High", color: "var(--color-fail)", meaning: "Clear signs of a fake or a bot" },
  CRITICAL: { word: "Critical", color: "var(--color-fail)", meaning: "Strong signs of a deepfake, spoof or bot" },
};

const TYPE_LABELS: Record<string, string> = {
  session: "Full verification",
  kyc: "Face and liveness",
  deepfake_image: "Face check (image)",
  deepfake_video: "Face check (video)",
  liveness_image: "Liveness (image)",
  liveness_video: "Liveness (video)",
  voice: "Voice check",
  behavior: "Typing check",
  voice_batch: "Voice check (batch)",
  batch: "Face check (batch)",
};

const typeLabel = (t?: string) => (t ? TYPE_LABELS[t] || t.replace(/_/g, " ") : "—");

function resultLabel(item: ActivityItem): { text: string; bad: boolean } | null {
  if (item.is_deepfake === null || item.is_deepfake === undefined) return null;
  if (item.type.startsWith("liveness")) return item.is_deepfake ? { text: "Spoof", bad: true } : { text: "Live", bad: false };
  return item.is_deepfake ? { text: "Flagged", bad: true } : { text: "Clean", bad: false };
}

function formatTime(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z"); // API sends UTC without a zone
  return d.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** 340 -> "340 ms", 6856 -> "6.9 s" */
function formatDuration(ms?: number) {
  if (!ms && ms !== 0) return "—";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <span className="block h-2 bg-rule/60 rounded-full overflow-hidden" aria-hidden="true">
      <span className="block h-full rounded-full" style={{ width: `${Math.max(pct, pct > 0 ? 2 : 0)}%`, background: color }} />
    </span>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
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
      <div className="max-w-6xl mx-auto px-6 py-24 flex items-center gap-3 text-ink-soft">
        <div className="spinner w-5 h-5" />
        Loading the dashboard…
      </div>
    );
  }

  const total = summary?.total_verifications || 0;
  const pctOf = (n: number) => (total ? Math.round((n / total) * 100) : 0);

  return (
    <div className="max-w-6xl mx-auto px-6 py-10 md:py-14">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[2rem] md:text-[2.5rem] font-bold leading-tight tracking-[-0.02em] text-ink">Dashboard</h1>
          <p className="mt-2 text-ink-soft">Every check run on this TrustGuard server, newest first.</p>
        </div>
        <Link href="/verify" className="btn self-start sm:self-auto">Start a verification</Link>
      </div>

      {!summary || total === 0 ? (
        <div className="sheet mt-10 px-6 py-14 text-center">
          <h2 className="text-xl font-bold text-ink">No verifications yet</h2>
          <p className="mt-2 text-ink-soft max-w-md mx-auto">
            Run a verification and its result, risk level and timing will appear here.
          </p>
          <Link href="/verify" className="btn mt-6">Start a verification</Link>
        </div>
      ) : (
        <>
          {/* Summary strip */}
          <dl className="mt-10 grid grid-cols-2 lg:grid-cols-4 border-y-2 border-ink">
            {[
              { label: "Checks run", value: total.toLocaleString() },
              { label: "Flagged as fake or bot", value: `${summary.deepfakes_caught.toLocaleString()}`, sub: `${pctOf(summary.deepfakes_caught)}% of all checks` },
              { label: "Came back clean", value: summary.clean_results.toLocaleString(), sub: `${pctOf(summary.clean_results)}% of all checks` },
              { label: "Average processing time", value: formatDuration(summary.avg_processing_time_ms) },
            ].map((s, i) => (
              <div
                key={s.label}
                className={`py-5 pr-4 ${i % 2 === 1 ? "pl-5 border-l border-rule" : ""} ${i === 2 ? "lg:pl-5 lg:border-l border-t lg:border-t-0 border-rule" : ""} ${i === 3 ? "border-t lg:border-t-0" : ""}`}
              >
                <dt className="text-sm text-ink-soft">{s.label}</dt>
                <dd className="mt-1 text-[1.75rem] font-bold leading-tight text-ink figures">{s.value}</dd>
                {s.sub && <dd className="text-sm text-ink-faint figures">{s.sub}</dd>}
              </div>
            ))}
          </dl>

          {/* Distributions */}
          <div className="mt-10 grid lg:grid-cols-2 gap-10">
            <section>
              <h2 className="text-lg font-bold text-ink">By check type</h2>
              <ul className="mt-4 space-y-4">
                {Object.entries(summary.by_type)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, count]) => (
                    <li key={type}>
                      <div className="flex justify-between gap-4 text-sm mb-1.5">
                        <span className="text-ink">{typeLabel(type)}</span>
                        <span className="text-ink-soft figures">{count} ({pctOf(count)}%)</span>
                      </div>
                      <Bar pct={pctOf(count)} color="var(--color-ink)" />
                    </li>
                  ))}
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-bold text-ink">By risk level</h2>
              <ul className="mt-4 space-y-4">
                {RISK_LEVELS.map((level) => {
                  const count = summary.by_risk_level[level] || 0;
                  const style = RISK_STYLE[level];
                  return (
                    <li key={level}>
                      <div className="flex justify-between gap-4 text-sm mb-1.5">
                        <span>
                          <span className="font-medium" style={{ color: style.color }}>{style.word}</span>
                          <span className="text-ink-faint"> — {style.meaning}</span>
                        </span>
                        <span className="text-ink-soft figures shrink-0">{count} ({pctOf(count)}%)</span>
                      </div>
                      <Bar pct={pctOf(count)} color={style.color} />
                    </li>
                  );
                })}
              </ul>
            </section>
          </div>
        </>
      )}

      {/* Recent activity */}
      <section className="mt-14">
        <h2 className="text-lg font-bold text-ink">Recent checks</h2>
        {activity.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left text-[0.9375rem]">
              <thead>
                <tr className="border-b-2 border-ink">
                  <th scope="col" className="py-2.5 pr-4 font-semibold">When</th>
                  <th scope="col" className="py-2.5 pr-4 font-semibold">Check</th>
                  <th scope="col" className="py-2.5 pr-4 font-semibold">Result</th>
                  <th scope="col" className="py-2.5 pr-4 font-semibold">Risk</th>
                  <th scope="col" className="py-2.5 font-semibold text-right">Time</th>
                </tr>
              </thead>
              <tbody className="figures">
                {activity.map((item) => {
                  const res = resultLabel(item);
                  const risk = item.risk_level ? RISK_STYLE[item.risk_level] : null;
                  return (
                    <tr key={item.id} className="border-b border-rule">
                      <td className="py-3 pr-4 text-ink-soft whitespace-nowrap">{formatTime(item.created_at)}</td>
                      <td className="py-3 pr-4 text-ink">{typeLabel(item.type)}</td>
                      <td className="py-3 pr-4">
                        {res ? (
                          <span className={res.bad ? "text-fail font-medium" : "text-pass font-medium"}>{res.text}</span>
                        ) : (
                          <span className="text-ink-faint">—</span>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        {risk ? <span style={{ color: risk.color }}>{risk.word}</span> : <span className="text-ink-faint">—</span>}
                      </td>
                      <td className="py-3 text-right text-ink-soft">
                        {formatDuration(item.processing_time_ms)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-4 text-ink-soft">Nothing yet. Each check you run is listed here.</p>
        )}
      </section>
    </div>
  );
}
