import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TrustGuard — AI-Powered Identity Verification",
  description:
    "Detect deepfakes, verify liveness, analyze voice authenticity, and check behavioral patterns — all in one platform with 99%+ accuracy.",
};

export default function Home() {
  return (
    <div className="relative">
      {/* Hero Section */}
      <section className="relative min-h-[85vh] flex items-center justify-center overflow-hidden">
        {/* Floating orbs */}
        <div className="orb w-[500px] h-[500px] bg-[#7b2ff7]/[0.07] top-[10%] left-[10%]" />
        <div className="orb w-[400px] h-[400px] bg-[#00d4ff]/[0.05] bottom-[10%] right-[15%]" style={{ animationDelay: '-5s' }} />
        <div className="orb w-[300px] h-[300px] bg-[#ff006e]/[0.04] top-[40%] right-[30%]" style={{ animationDelay: '-10s' }} />

        <div className="relative max-w-5xl mx-auto px-6 text-center">
          {/* Badge */}
          <div className="fade-up stagger-1">
            <div className="inline-flex items-center gap-2 text-[11px] font-medium text-white/50 border border-white/[0.08] rounded-full px-4 py-1.5 mb-8 backdrop-blur-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80] animate-pulse" />
              4 AI Agents Working Together
            </div>
          </div>

          {/* Headline */}
          <h1 className="fade-up stagger-2 text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[0.95] mb-6">
            <span className="text-white">Is this person</span>
            <br />
            <span className="gradient-text">real or fake?</span>
          </h1>

          {/* Subhead */}
          <p className="fade-up stagger-3 text-base md:text-lg text-white/35 max-w-xl mx-auto mb-10 leading-relaxed">
            One selfie. One voice clip. One typing test.
            <br className="hidden md:block" />
            Four independent AI agents. One trust score.
          </p>

          {/* CTAs */}
          <div className="fade-up stagger-4 flex flex-col sm:flex-row gap-3 justify-center items-center">
            <Link
              href="/verify"
              className="btn-glow text-white px-8 py-3.5 rounded-xl text-sm font-semibold tracking-wide"
            >
              Start Verification
            </Link>
            <Link
              href="/dashboard"
              className="group flex items-center gap-2 text-white/30 hover:text-white/60 text-sm font-medium transition-colors duration-300 px-6 py-3.5"
            >
              View Dashboard
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="group-hover:translate-x-0.5 transition-transform">
                <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </Link>
          </div>

          {/* Stats bar */}
          <div className="fade-up stagger-5 mt-16 flex items-center justify-center gap-8 md:gap-14">
            {[
              { value: "99.3%", label: "Model Accuracy" },
              { value: "4", label: "AI Agents" },
              { value: "<5s", label: "Verification" },
              { value: "90+", label: "Tests Passing" },
            ].map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-lg md:text-xl font-bold text-white/80 font-mono">{stat.value}</div>
                <div className="text-[10px] text-white/20 uppercase tracking-widest mt-0.5">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="section-line max-w-5xl mx-auto" />

      {/* Problem Statement */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="fade-up text-center mb-14">
          <p className="text-[11px] uppercase tracking-[0.2em] text-white/20 mb-3">The Problem</p>
          <h2 className="text-3xl md:text-4xl font-bold text-white/90 tracking-tight">
            Single checks get fooled.
          </h2>
          <p className="text-white/30 mt-3 max-w-lg mx-auto text-sm leading-relaxed">
            Photo-of-a-photo. Voice cloning. Automated bots. Each targets one weakness.
            TrustGuard runs 4 independent checks — even if one is fooled, the others catch it.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          {/* Agent 1 - Large */}
          <div className="md:col-span-4 glass glow-border shimmer-hover rounded-2xl p-7 fade-up stagger-1">
            <div className="flex items-start justify-between mb-5">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#00d4ff]/20 to-[#00d4ff]/5 flex items-center justify-center border border-[#00d4ff]/10">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2"/>
                      <circle cx="8.5" cy="8.5" r="1.5"/>
                      <path d="M21 15l-5-5L5 21"/>
                    </svg>
                  </div>
                  <h3 className="text-base font-semibold text-white/90">Deepfake Detection</h3>
                </div>
              </div>
              <span className="text-[10px] font-mono text-[#00d4ff]/60 bg-[#00d4ff]/[0.06] px-2.5 py-1 rounded-full">
                30% weight
              </span>
            </div>
            <p className="text-sm text-white/30 leading-relaxed mb-5">
              Vision Transformer (ViT) model trained on deepfake datasets. Analyzes pixel-level
              patterns that distinguish real photos from AI-generated faces.
            </p>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-[11px] bg-[#4ade80]/[0.06] text-[#4ade80]/80 px-3 py-1.5 rounded-lg border border-[#4ade80]/10">
                <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80]" />
                99.27% accuracy
              </div>
              <span className="text-[11px] text-white/15 font-mono">HuggingFace ViT</span>
            </div>
          </div>

          {/* Agent 2 - Small */}
          <div className="md:col-span-2 glass glow-border shimmer-hover rounded-2xl p-7 fade-up stagger-2 flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#7b2ff7]/20 to-[#7b2ff7]/5 flex items-center justify-center border border-[#7b2ff7]/10 mb-4">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7b2ff7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <h3 className="text-base font-semibold text-white/90 mb-1">Liveness</h3>
              <span className="text-[10px] font-mono text-[#7b2ff7]/60">25% weight</span>
            </div>
            <div className="mt-5">
              <p className="text-sm text-white/30 leading-relaxed mb-4">
                6 independent checks using OpenCV + MediaPipe. Catches photo-of-photo and screen replay.
              </p>
              <div className="flex gap-1.5">
                {[1,2,3,4,5,6].map(n => (
                  <div key={n} className="w-6 h-1 rounded-full bg-[#7b2ff7]/20" />
                ))}
              </div>
              <p className="text-[10px] text-white/15 mt-1.5 font-mono">6 signal checks</p>
            </div>
          </div>

          {/* Agent 3 - Small */}
          <div className="md:col-span-2 glass glow-border shimmer-hover rounded-2xl p-7 fade-up stagger-3 flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#4ade80]/20 to-[#4ade80]/5 flex items-center justify-center border border-[#4ade80]/10 mb-4">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="22"/>
                </svg>
              </div>
              <h3 className="text-base font-semibold text-white/90 mb-1">Voice Analysis</h3>
              <span className="text-[10px] font-mono text-[#4ade80]/60">25% weight</span>
            </div>
            <div className="mt-5">
              <p className="text-sm text-white/30 leading-relaxed mb-4">
                HuggingFace cloud API primary, local spectral analysis fallback. Works offline.
              </p>
              <div className="text-[11px] text-white/15 font-mono">2-tier detection</div>
            </div>
          </div>

          {/* Agent 4 - Large */}
          <div className="md:col-span-4 glass glow-border shimmer-hover rounded-2xl p-7 fade-up stagger-4">
            <div className="flex items-start justify-between mb-5">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#fbbf24]/20 to-[#fbbf24]/5 flex items-center justify-center border border-[#fbbf24]/10">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"/>
                    </svg>
                  </div>
                  <h3 className="text-base font-semibold text-white/90">Behavioral Biometrics</h3>
                </div>
              </div>
              <span className="text-[10px] font-mono text-[#fbbf24]/60 bg-[#fbbf24]/[0.06] px-2.5 py-1 rounded-full">
                20% weight
              </span>
            </div>
            <p className="text-sm text-white/30 leading-relaxed mb-5">
              Pure rule-based analysis — no ML needed. Checks typing speed (bots type &lt;30ms between keys),
              rhythm variance, mouse speed, and path straightness.
            </p>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-[11px] bg-[#fbbf24]/[0.06] text-[#fbbf24]/80 px-3 py-1.5 rounded-lg border border-[#fbbf24]/10">
                Catches automated bots
              </div>
              <span className="text-[11px] text-white/15 font-mono">No training data needed</span>
            </div>
          </div>
        </div>
      </section>

      <div className="section-line max-w-5xl mx-auto" />

      {/* Scoring Section */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="fade-up text-center mb-14">
          <p className="text-[11px] uppercase tracking-[0.2em] text-white/20 mb-3">Scoring</p>
          <h2 className="text-3xl md:text-4xl font-bold text-white/90 tracking-tight">
            One score. Full transparency.
          </h2>
        </div>

        <div className="grid md:grid-cols-2 gap-3">
          {/* Formula */}
          <div className="glass rounded-2xl p-7 fade-up stagger-1">
            <p className="text-[11px] uppercase tracking-[0.15em] text-white/20 mb-5">Weighted Formula</p>
            <div className="space-y-3 font-mono text-sm">
              {[
                { name: "Deepfake", color: "#00d4ff", weight: "0.30" },
                { name: "Liveness", color: "#7b2ff7", weight: "0.25" },
                { name: "Voice", color: "#4ade80", weight: "0.25" },
                { name: "Behavior", color: "#fbbf24", weight: "0.20" },
              ].map((agent) => (
                <div key={agent.name} className="flex items-center justify-between py-2 border-b border-white/[0.03]">
                  <div className="flex items-center gap-2.5">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: agent.color, opacity: 0.7 }} />
                    <span className="text-white/50">{agent.name}</span>
                  </div>
                  <span className="text-white/20">&times; {agent.weight}</span>
                </div>
              ))}
              <div className="flex items-center justify-between pt-2">
                <span className="text-white/70 font-semibold">=&nbsp; Trust Score</span>
                <span className="text-white/40">0 &ndash; 100</span>
              </div>
            </div>
            <p className="text-[11px] text-white/15 mt-4">
              Skipped agents redistribute weight automatically.
            </p>
          </div>

          {/* Decisions */}
          <div className="glass rounded-2xl p-7 fade-up stagger-2">
            <p className="text-[11px] uppercase tracking-[0.15em] text-white/20 mb-5">Decisions</p>
            <div className="space-y-3">
              {[
                {
                  decision: "PASS",
                  range: "70+",
                  color: "#4ade80",
                  bg: "rgba(74, 222, 128, 0.04)",
                  border: "rgba(74, 222, 128, 0.1)",
                  desc: "All agents agree, no high-risk flags",
                },
                {
                  decision: "REVIEW",
                  range: "40-69",
                  color: "#fbbf24",
                  bg: "rgba(251, 191, 36, 0.04)",
                  border: "rgba(251, 191, 36, 0.1)",
                  desc: "Some concerns — 1 agent flagged HIGH risk",
                },
                {
                  decision: "FAIL",
                  range: "<40",
                  color: "#f87171",
                  bg: "rgba(248, 113, 113, 0.04)",
                  border: "rgba(248, 113, 113, 0.1)",
                  desc: "Critical risk, or 2+ agents flagged — likely fake",
                },
              ].map((d) => (
                <div
                  key={d.decision}
                  className="flex items-center gap-4 rounded-xl p-4 transition-colors duration-300"
                  style={{ background: d.bg, border: `1px solid ${d.border}` }}
                >
                  <div
                    className="text-xs font-bold font-mono px-2.5 py-1 rounded-md"
                    style={{ color: d.color, background: `${d.color}10` }}
                  >
                    {d.decision}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm text-white/50">{d.desc}</div>
                  </div>
                  <span className="text-xs font-mono text-white/20">{d.range}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="section-line max-w-5xl mx-auto" />

      {/* How It Works */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="fade-up text-center mb-14">
          <p className="text-[11px] uppercase tracking-[0.2em] text-white/20 mb-3">Process</p>
          <h2 className="text-3xl md:text-4xl font-bold text-white/90 tracking-tight">
            Three inputs. Four agents. One score.
          </h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            {
              step: "01",
              title: "Selfie",
              desc: "Camera capture or upload. Face validated before proceeding.",
              color: "#00d4ff",
            },
            {
              step: "02",
              title: "Voice",
              desc: "Read a random phrase. Short/silent recordings rejected.",
              color: "#7b2ff7",
            },
            {
              step: "03",
              title: "Typing",
              desc: "Type a sentence. Keystroke timing + mouse patterns tracked.",
              color: "#4ade80",
            },
            {
              step: "04",
              title: "Score",
              desc: "Trust score, decision, per-agent breakdown, and audit trail.",
              color: "#fbbf24",
            },
          ].map((s, i) => (
            <div key={i} className={`glass shimmer-hover rounded-2xl p-6 text-center fade-up stagger-${i + 1}`}>
              <div
                className="text-3xl font-bold font-mono mb-3"
                style={{ color: s.color, opacity: 0.15 }}
              >
                {s.step}
              </div>
              <h3 className="text-sm font-semibold text-white/80 mb-2">{s.title}</h3>
              <p className="text-[12px] text-white/25 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="section-line max-w-5xl mx-auto" />

      {/* Tech Stack */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="fade-up text-center mb-10">
          <p className="text-[11px] uppercase tracking-[0.2em] text-white/20 mb-3">Stack</p>
          <h2 className="text-2xl font-bold text-white/90 tracking-tight">Built With</h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 fade-up">
          {[
            { name: "FastAPI", detail: "Python backend", color: "#009688" },
            { name: "Next.js 16", detail: "React frontend", color: "#ffffff" },
            { name: "PyTorch + ViT", detail: "Deepfake model", color: "#ee4c2c" },
            { name: "MediaPipe", detail: "Face detection", color: "#4285f4" },
            { name: "SQLAlchemy", detail: "Database ORM", color: "#d71f00" },
            { name: "HuggingFace", detail: "ML model hub", color: "#ff9d00" },
            { name: "Tailwind CSS", detail: "UI styling", color: "#38bdf8" },
            { name: "pytest", detail: "90 tests passing", color: "#4ade80" },
          ].map((t, i) => (
            <div
              key={i}
              className="glass rounded-xl p-4 text-center hover:bg-white/[0.03] transition-colors"
            >
              <p className="text-xs font-semibold font-mono" style={{ color: t.color, opacity: 0.7 }}>
                {t.name}
              </p>
              <p className="text-[10px] text-white/15 mt-1">{t.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="section-line max-w-5xl mx-auto" />

      {/* CTA */}
      <section className="max-w-5xl mx-auto px-6 py-24 text-center">
        <div className="fade-up">
          <h2 className="text-3xl md:text-4xl font-bold text-white/90 tracking-tight mb-4">
            Ready to verify?
          </h2>
          <p className="text-white/25 text-sm mb-8 max-w-md mx-auto">
            Selfie, voice, behavior — see your trust score in under 5 seconds.
          </p>
          <Link
            href="/verify"
            className="btn-glow text-white px-10 py-4 rounded-xl text-sm font-semibold tracking-wide inline-block"
          >
            Start Verification
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.03] py-6 text-center">
        <p className="text-[11px] text-white/15">
          TrustGuard v1.0.0 &middot; Built by Ashmeet Singh &middot;{" "}
          <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`} className="text-white/20 hover:text-white/40 transition-colors">
            API Docs
          </a>
        </p>
      </footer>
    </div>
  );
}
