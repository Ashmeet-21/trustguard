"use client";

import { useState } from "react";
import StepWizard from "@/components/StepWizard";
import CameraCapture from "@/components/CameraCapture";
import AudioRecorder from "@/components/AudioRecorder";
import BehavioralTracker from "@/components/BehavioralTracker";
import TrustScoreGauge from "@/components/TrustScoreGauge";
import AgentStatusCard from "@/components/AgentStatusCard";
import { createSession, runVerification, type SessionResult } from "@/lib/api";
import type { BehaviorData } from "@/components/BehavioralTracker";

const steps = [
  { label: "Selfie", icon: "📷" },
  { label: "Voice", icon: "🎤" },
  { label: "Behavior", icon: "⌨️" },
  { label: "Processing", icon: "⚙️" },
  { label: "Results", icon: "✓" },
];

export default function VerifyPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [behaviorData, setBehaviorData] = useState<BehaviorData | null>(null);
  const [result, setResult] = useState<SessionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  const handleImageCapture = (file: File) => {
    setImageFile(file);
  };

  const handleAudioRecording = (blob: Blob) => {
    setAudioBlob(blob);
  };

  const handleBehaviorComplete = (data: BehaviorData) => {
    setBehaviorData(data);
  };

  const nextStep = () => setCurrentStep((s) => s + 1);
  const prevStep = () => setCurrentStep((s) => Math.max(0, s - 1));

  const runFullVerification = async () => {
    setCurrentStep(3); // Processing step
    setProcessing(true);
    setError(null);

    try {
      const session = await createSession();
      const res = await runVerification(
        session.session_id,
        imageFile || undefined,
        audioBlob || undefined,
        behaviorData || undefined
      );
      setResult(res);
      setCurrentStep(4); // Results step
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
      setCurrentStep(2); // Back to last input step
    } finally {
      setProcessing(false);
    }
  };

  const restart = () => {
    setCurrentStep(0);
    setImageFile(null);
    setAudioBlob(null);
    setBehaviorData(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <h1 className="text-3xl font-bold text-center mb-2 gradient-text">
        Identity Verification
      </h1>
      <p className="text-center text-[#666] text-sm mb-8">
        Complete the steps below to verify your identity
      </p>

      <StepWizard steps={steps} currentStep={currentStep} />

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4 mb-6 text-sm">
          {error}
        </div>
      )}

      <div className="bg-[#111] border border-[#222] rounded-2xl p-6">
        {/* Step 0: Selfie */}
        {currentStep === 0 && (
          <div>
            <h2 className="text-lg font-semibold mb-1">Step 1: Take a Selfie</h2>
            <p className="text-sm text-[#666] mb-4">
              Use your webcam or upload a photo. This checks for deepfakes and liveness.
            </p>
            <CameraCapture onCapture={handleImageCapture} />
            <div className="flex justify-between mt-6">
              <div />
              <button
                onClick={nextStep}
                disabled={!imageFile}
                className="gradient-bg text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Next: Voice Sample →
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Voice */}
        {currentStep === 1 && (
          <div>
            <h2 className="text-lg font-semibold mb-1">Step 2: Voice Sample</h2>
            <p className="text-sm text-[#666] mb-4">
              Record yourself reading the phrase below. This checks for synthetic voice.
            </p>
            <AudioRecorder onRecording={handleAudioRecording} />
            <div className="flex justify-between mt-6">
              <button
                onClick={prevStep}
                className="text-[#666] hover:text-white text-sm transition"
              >
                ← Back
              </button>
              <div className="flex gap-3">
                <button
                  onClick={nextStep}
                  className="text-[#666] hover:text-white text-sm border border-[#333] px-4 py-2 rounded-lg transition"
                >
                  Skip
                </button>
                <button
                  onClick={nextStep}
                  disabled={!audioBlob}
                  className="gradient-bg text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Next: Behavior Test →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Behavior */}
        {currentStep === 2 && (
          <div>
            <h2 className="text-lg font-semibold mb-1">Step 3: Behavioral Test</h2>
            <p className="text-sm text-[#666] mb-4">
              Type the sentence below while moving your mouse. This checks for bot-like patterns.
            </p>
            <BehavioralTracker onComplete={handleBehaviorComplete} />
            <div className="flex justify-between mt-6">
              <button
                onClick={prevStep}
                className="text-[#666] hover:text-white text-sm transition"
              >
                ← Back
              </button>
              <div className="flex gap-3">
                <button
                  onClick={runFullVerification}
                  className="text-[#666] hover:text-white text-sm border border-[#333] px-4 py-2 rounded-lg transition"
                >
                  Skip & Submit
                </button>
                <button
                  onClick={runFullVerification}
                  disabled={!behaviorData}
                  className="gradient-bg text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Submit for Verification →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Processing */}
        {currentStep === 3 && processing && (
          <div className="text-center py-16">
            <div className="animate-spin w-12 h-12 border-4 border-[#333] border-t-[#7b2ff7] rounded-full mx-auto mb-6" />
            <h2 className="text-lg font-semibold mb-2">Running Verification</h2>
            <p className="text-sm text-[#666]">
              Analyzing your selfie, voice, and behavior patterns...
            </p>
            <div className="mt-6 space-y-2 text-sm text-[#888]">
              {imageFile && <p>🖼️ Running deepfake + liveness detection...</p>}
              {audioBlob && <p>🎤 Analyzing voice sample...</p>}
              {behaviorData && <p>⌨️ Checking behavioral patterns...</p>}
              <p>🧠 Calculating trust score...</p>
            </div>
          </div>
        )}

        {/* Step 4: Results */}
        {currentStep === 4 && result && (
          <div>
            <div className="text-center mb-8">
              <div className="relative inline-block">
                <TrustScoreGauge score={result.trust_score} decision={result.decision} />
              </div>
            </div>

            {/* Agent Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              {Object.entries(result.agents).map(([name, agent]) => (
                <AgentStatusCard key={name} name={name} result={agent} />
              ))}
            </div>

            {/* Explanation */}
            {result.explanation && result.explanation.length > 0 && (
              <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-4 mb-6">
                <h3 className="text-sm font-medium text-[#999] mb-2 uppercase tracking-wider">Explanation</h3>
                <ul className="space-y-1">
                  {result.explanation.map((line, i) => (
                    <li key={i} className="text-sm text-[#888]">
                      {line}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Quality Gates */}
            {result.quality_gates && result.quality_gates.length > 0 && (
              <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-4 mb-6">
                <h3 className="text-sm font-medium text-[#999] mb-2 uppercase tracking-wider">Quality Gates</h3>
                <div className="flex flex-wrap gap-2">
                  {result.quality_gates.map((gate, i) => (
                    <span
                      key={i}
                      className={`text-xs px-3 py-1 rounded-full ${
                        gate.passed
                          ? "bg-[#0d2e1a] text-[#4ade80] border border-[#166534]"
                          : "bg-[#2e0d0d] text-[#f87171] border border-[#7f1d1d]"
                      }`}
                    >
                      {gate.passed ? "✓" : "✗"} {gate.gate.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between text-xs text-[#555]">
              <span>Session: {result.session_id.slice(0, 8)}...</span>
              <span>Processed in {result.processing_time_ms}ms</span>
            </div>

            <div className="text-center mt-6">
              <button
                onClick={restart}
                className="gradient-bg text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition"
              >
                Verify Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
