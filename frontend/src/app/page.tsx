import Link from "next/link";

export default function Home() {
  const features = [
    {
      icon: "🖼️",
      title: "Deepfake Detection",
      desc: "Vision Transformer model detects AI-generated faces with 99%+ accuracy",
    },
    {
      icon: "👤",
      title: "Liveness Detection",
      desc: "6 independent checks verify the person is live, not a photo or screen replay",
    },
    {
      icon: "🎤",
      title: "Voice Analysis",
      desc: "Spectral analysis and HuggingFace API detect synthetic or cloned voices",
    },
    {
      icon: "⌨️",
      title: "Behavioral Biometrics",
      desc: "Keystroke timing and mouse patterns distinguish humans from bots",
    },
    {
      icon: "🧠",
      title: "Risk Engine",
      desc: "Weighted multi-signal scoring combines all agents into a single trust score",
    },
    {
      icon: "📋",
      title: "Audit Trail",
      desc: "Complete audit reports with quality gates for every verification session",
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      {/* Hero */}
      <div className="text-center mb-20">
        <h1 className="text-5xl md:text-6xl font-bold mb-4 gradient-text">
          Identity Verification
        </h1>
        <p className="text-lg text-[#888] max-w-2xl mx-auto mb-8">
          Multi-modal AI platform that combines deepfake detection, liveness checks,
          voice analysis, and behavioral biometrics into a single trust score.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/verify"
            className="gradient-bg text-white px-8 py-3 rounded-xl text-base font-semibold hover:opacity-90 transition"
          >
            Start Verification
          </Link>
          <Link
            href="/dashboard"
            className="bg-[#111] text-white border border-[#333] px-8 py-3 rounded-xl text-base font-medium hover:bg-[#1a1a1a] transition"
          >
            View Dashboard
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16">
        {[
          { num: "4", label: "Detection Agents" },
          { num: "6", label: "Liveness Checks" },
          { num: "88", label: "Tests Passing" },
          { num: "100", label: "Trust Score Range" },
        ].map((s, i) => (
          <div key={i} className="bg-[#111] border border-[#222] rounded-xl p-5 text-center">
            <div className="text-3xl font-bold gradient-text">{s.num}</div>
            <div className="text-xs text-[#555] mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Features */}
      <h2 className="text-2xl font-bold text-center mb-8">Detection Pipeline</h2>
      <div className="grid md:grid-cols-3 gap-4 mb-16">
        {features.map((f, i) => (
          <div
            key={i}
            className="bg-[#111] border border-[#222] rounded-xl p-6 hover:border-[#333] transition"
          >
            <div className="text-3xl mb-3">{f.icon}</div>
            <h3 className="text-base font-semibold text-white mb-2">{f.title}</h3>
            <p className="text-sm text-[#888]">{f.desc}</p>
          </div>
        ))}
      </div>

      {/* How it works */}
      <h2 className="text-2xl font-bold text-center mb-8">How It Works</h2>
      <div className="flex flex-col md:flex-row gap-4 mb-16">
        {[
          { step: "1", title: "Selfie", desc: "Take a photo or upload an image" },
          { step: "2", title: "Voice", desc: "Record a short voice sample" },
          { step: "3", title: "Behavior", desc: "Type a sentence while we track patterns" },
          { step: "4", title: "Result", desc: "Get trust score + PASS/REVIEW/FAIL verdict" },
        ].map((s, i) => (
          <div key={i} className="flex-1 bg-[#111] border border-[#222] rounded-xl p-5 text-center">
            <div className="w-8 h-8 gradient-bg rounded-full flex items-center justify-center text-white font-bold text-sm mx-auto mb-3">
              {s.step}
            </div>
            <h3 className="font-semibold text-white mb-1">{s.title}</h3>
            <p className="text-sm text-[#888]">{s.desc}</p>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="text-center text-[#333] text-xs border-t border-[#1a1a1a] pt-6">
        TrustGuard v1.0.0 &middot; Built by Ashmeet Singh &middot;{" "}
        <a href="http://localhost:8000/docs" className="text-[#555] hover:text-[#999]">API Docs</a>
      </div>
    </div>
  );
}
