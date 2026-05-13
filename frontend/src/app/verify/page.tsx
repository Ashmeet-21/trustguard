"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import StepWizard from "@/components/StepWizard";
import CameraCapture from "@/components/CameraCapture";
import AudioRecorder from "@/components/AudioRecorder";
import BehavioralTracker from "@/components/BehavioralTracker";
import TrustScoreGauge from "@/components/TrustScoreGauge";
import AgentStatusCard from "@/components/AgentStatusCard";
import {
  createSession,
  runVerification,
  checkFace,
  type SessionResult,
} from "@/lib/api";
import type { BehaviorData } from "@/components/BehavioralTracker";

/** Plain English quality gate labels */
function gateInfo(gate: string, passed: boolean): { title: string; description: string } {
  switch (gate) {
    case "replay_protection":
      return passed
        ? { title: "Not a Replay", description: "This image hasn't been submitted before — it's a fresh upload." }
        : { title: "Replay Detected", description: "This exact image was already submitted in a previous session. Please use a new photo to prevent reuse attacks." };
    case "minimum_signals":
      return passed
        ? { title: "Enough Data Collected", description: "At least 2 verification checks ran successfully, giving us reliable results." }
        : { title: "Not Enough Data", description: "Only 1 verification check completed. We need at least 2 (e.g. selfie + voice) for a reliable result. Try adding more inputs." };
    case "signal_agreement":
      return passed
        ? { title: "Checks Agree", description: "All verification agents reached similar conclusions — the results are consistent." }
        : { title: "Checks Disagree", description: "The agents gave conflicting results (e.g. one says safe, another says risky). This is suspicious and needs review." };
    default:
      return passed
        ? { title: gate.replace(/_/g, " "), description: "This check passed." }
        : { title: gate.replace(/_/g, " "), description: "This check failed." };
  }
}

const steps = [
  { label: "Selfie", icon: "01" },
  { label: "Voice", icon: "02" },
  { label: "Behavior", icon: "03" },
  { label: "Processing", icon: "04" },
  { label: "Results", icon: "05" },
];

export default function VerifyPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  const [currentStep, setCurrentStep] = useState(0);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [behaviorData, setBehaviorData] = useState<BehaviorData | null>(null);
  const [result, setResult] = useState<SessionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  // Face validation state
  const [faceChecking, setFaceChecking] = useState(false);
  const [faceValid, setFaceValid] = useState(false);
  const [faceError, setFaceError] = useState<string | null>(null);

  if (authLoading || !user) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-20 text-center">
        <div className="spinner w-10 h-10 mx-auto mb-4" />
        <p className="text-white/25 text-sm">Loading...</p>
      </div>
    );
  }

  const handleImageCapture = async (file: File) => {
    setImageFile(file);
    setFaceError(null);
    setFaceValid(false);
    setFaceChecking(true);

    try {
      const result = await checkFace(file);
      if (!result.faceDetected) {
        setFaceError(
          "No face detected. Please take a clear selfie showing your full face within the oval guide."
        );
        setImageFile(null);
      } else if (result.faceBbox) {
        const bbox = result.faceBbox;
        const EDGE = 0.04;
        const cutSides: string[] = [];
        if (bbox.x_min < EDGE) cutSides.push("left");
        if (bbox.y_min < EDGE) cutSides.push("top");
        if (bbox.x_max > 1 - EDGE) cutSides.push("right");
        if (bbox.y_max > 1 - EDGE) cutSides.push("bottom");

        if (cutSides.length > 0) {
          setFaceError(
            `Face is cut off at the ${cutSides.join(" and ")}. Please center your full face within the oval guide — no half face or cropped photos.`
          );
          setImageFile(null);
        } else if (bbox.width_pct < 0.15 || bbox.height_pct < 0.18) {
          setFaceError(
            "Face is too small in the photo. Please move closer to the camera so your face fills the oval guide."
          );
          setImageFile(null);
        } else if (result.livenessScore < 0.3) {
          setFaceError(
            "Photo quality is too low — it appears blurry or taken from a screen. Please take a clear, well-lit selfie directly with your camera."
          );
          setImageFile(null);
        } else if (result.livenessScore < 0.5) {
          setFaceError(
            "Photo is unclear or blurry. Please ensure good lighting and hold your camera steady for a sharp selfie."
          );
          setImageFile(null);
        } else {
          setFaceValid(true);
        }
      } else {
        setFaceValid(true);
      }
    } catch {
      setFaceValid(true);
    } finally {
      setFaceChecking(false);
    }
  };

  const handleAudioRecording = (blob: Blob) => {
    setAudioBlob(blob);
  };

  const handleBehaviorComplete = (data: BehaviorData) => {
    setBehaviorData(data);
  };

  const handleImageReset = () => {
    setImageFile(null);
    setFaceValid(false);
    setFaceError(null);
  };

  const handleAudioReset = () => {
    setAudioBlob(null);
  };

  const handleBehaviorReset = () => {
    setBehaviorData(null);
  };

  const nextStep = () => setCurrentStep((s) => s + 1);
  const prevStep = () => setCurrentStep((s) => Math.max(0, s - 1));

  const runFullVerification = async () => {
    setCurrentStep(3);
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
      setCurrentStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
      setCurrentStep(2);
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
    setFaceValid(false);
    setFaceError(null);
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      {/* Header */}
      <div className="text-center mb-10 fade-up">
        <p className="text-[11px] uppercase tracking-[0.2em] text-white/20 mb-3">Verification</p>
        <h1 className="text-3xl md:text-4xl font-bold text-white/90 tracking-tight">
          Identity Verification
        </h1>
        <p className="text-white/30 text-sm mt-2">
          Complete the steps below to verify your identity
        </p>
      </div>

      <div className="fade-up stagger-1">
        <StepWizard steps={steps} currentStep={currentStep} />
      </div>

      {error && (
        <div className="glass rounded-xl p-4 mb-6 text-sm border-[#f87171]/20 bg-[#f87171]/[0.04] fade-up" style={{ borderColor: 'rgba(248, 113, 113, 0.15)' }}>
          <span className="text-[#f87171]/80">{error}</span>
        </div>
      )}

      <div className="glass rounded-2xl p-7 fade-up stagger-2">
        {/* Step 0: Selfie */}
        {currentStep === 0 && (
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-7 h-7 rounded-lg bg-[#00d4ff]/[0.08] flex items-center justify-center border border-[#00d4ff]/10">
                <span className="text-[10px] font-mono font-bold text-[#00d4ff]/60">01</span>
              </div>
              <h2 className="text-base font-semibold text-white/80">Take a Selfie</h2>
            </div>
            <p className="text-sm text-white/25 mb-5 ml-10">
              Use your webcam or upload a photo. This checks for deepfakes and liveness.
            </p>
            <CameraCapture onCapture={handleImageCapture} onReset={handleImageReset} />

            {faceChecking && (
              <div className="flex items-center gap-2.5 mt-4 text-sm text-white/30">
                <div className="spinner w-4 h-4" />
                Checking for face...
              </div>
            )}

            {faceValid && !faceChecking && (
              <div className="glass rounded-lg p-3 mt-4 text-sm flex items-center gap-2" style={{ background: 'rgba(74, 222, 128, 0.04)', borderColor: 'rgba(74, 222, 128, 0.1)' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80]" />
                <span className="text-[#4ade80]/80">Face detected — ready to proceed</span>
              </div>
            )}

            {faceError && (
              <div className="glass rounded-lg p-3 mt-4 text-sm" style={{ background: 'rgba(248, 113, 113, 0.04)', borderColor: 'rgba(248, 113, 113, 0.1)' }}>
                <span className="text-[#f87171]/80">{faceError}</span>
              </div>
            )}

            <div className="flex justify-between mt-8">
              <div />
              <button
                onClick={nextStep}
                disabled={!imageFile || !faceValid || faceChecking}
                className="btn-glow text-white px-6 py-2.5 rounded-xl text-sm font-medium disabled:opacity-20 disabled:cursor-not-allowed disabled:transform-none"
              >
                Next: Voice Sample
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Voice */}
        {currentStep === 1 && (
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-7 h-7 rounded-lg bg-[#7b2ff7]/[0.08] flex items-center justify-center border border-[#7b2ff7]/10">
                <span className="text-[10px] font-mono font-bold text-[#7b2ff7]/60">02</span>
              </div>
              <h2 className="text-base font-semibold text-white/80">Voice Sample</h2>
            </div>
            <p className="text-sm text-white/25 mb-5 ml-10">
              Record yourself reading the phrase below. This checks for synthetic voice.
            </p>
            <AudioRecorder onRecording={handleAudioRecording} onReset={handleAudioReset} />
            <div className="flex justify-between mt-8">
              <button
                onClick={prevStep}
                className="text-white/20 hover:text-white/50 text-sm transition-colors duration-300"
              >
                Back
              </button>
              <button
                onClick={nextStep}
                disabled={!audioBlob}
                className="btn-glow text-white px-6 py-2.5 rounded-xl text-sm font-medium disabled:opacity-20 disabled:cursor-not-allowed disabled:transform-none"
              >
                Next: Behavior Test
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Behavior */}
        {currentStep === 2 && (
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-7 h-7 rounded-lg bg-[#4ade80]/[0.08] flex items-center justify-center border border-[#4ade80]/10">
                <span className="text-[10px] font-mono font-bold text-[#4ade80]/60">03</span>
              </div>
              <h2 className="text-base font-semibold text-white/80">Behavioral Test</h2>
            </div>
            <p className="text-sm text-white/25 mb-5 ml-10">
              Type the sentence below while moving your mouse. This checks for bot-like patterns.
            </p>
            <BehavioralTracker onComplete={handleBehaviorComplete} onReset={handleBehaviorReset} />
            <div className="flex justify-between mt-8">
              <button
                onClick={prevStep}
                className="text-white/20 hover:text-white/50 text-sm transition-colors duration-300"
              >
                Back
              </button>
              <button
                onClick={runFullVerification}
                disabled={!behaviorData}
                className="btn-glow text-white px-6 py-2.5 rounded-xl text-sm font-medium disabled:opacity-20 disabled:cursor-not-allowed disabled:transform-none"
              >
                Submit for Verification
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Processing */}
        {currentStep === 3 && processing && (
          <div className="text-center py-20">
            <div className="relative w-16 h-16 mx-auto mb-8">
              <div className="spinner w-16 h-16 border-[3px]" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-[#7b2ff7]/50 animate-pulse" />
              </div>
            </div>
            <h2 className="text-base font-semibold text-white/70 mb-2">
              Running Verification
            </h2>
            <p className="text-sm text-white/25 mb-6">
              Analyzing your selfie, voice, and behavior patterns...
            </p>
            <div className="space-y-1.5 text-[12px] text-white/15 font-mono">
              {imageFile && <p>deepfake_agent: running...</p>}
              {imageFile && <p>liveness_agent: running...</p>}
              {audioBlob && <p>voice_agent: running...</p>}
              {behaviorData && <p>behavior_agent: running...</p>}
              <p>risk_engine: waiting...</p>
            </div>
          </div>
        )}

        {/* Step 4: Results */}
        {currentStep === 4 && result && (
          <div>
            <div className="text-center mb-8">
              <div className="relative inline-block">
                <TrustScoreGauge
                  score={result.trust_score}
                  decision={result.decision}
                />
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
              <div className="glass rounded-xl p-5 mb-4">
                <p className="text-[10px] uppercase tracking-[0.15em] text-white/20 mb-3">Explanation</p>
                <ul className="space-y-1.5">
                  {result.explanation.map((line, i) => (
                    <li key={i} className="text-sm text-white/35 flex items-start gap-2">
                      <span className="text-white/10 mt-0.5">&mdash;</span>
                      {line}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Quality Gates */}
            {result.quality_gates && result.quality_gates.length > 0 && (
              <div className="glass rounded-xl p-5 mb-6">
                <p className="text-[10px] uppercase tracking-[0.15em] text-white/20 mb-4">Quality Checks</p>
                <div className="space-y-2">
                  {result.quality_gates.map((gate, i) => {
                    const info = gateInfo(gate.gate, gate.passed);
                    const color = gate.passed ? "#4ade80" : "#f87171";
                    return (
                      <div
                        key={i}
                        className="flex items-start gap-3 text-sm rounded-lg p-3"
                        style={{
                          background: `${color}06`,
                          border: `1px solid ${color}15`,
                        }}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                          style={{ backgroundColor: color, opacity: 0.7 }}
                        />
                        <div>
                          <p className="font-medium" style={{ color, opacity: 0.8 }}>
                            {info.title}
                          </p>
                          <p className="text-[12px] text-white/25 mt-0.5">{info.description}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between text-[11px] text-white/15 font-mono">
              <span>session: {result.session_id.slice(0, 8)}...</span>
              <span>{result.processing_time_ms}ms</span>
            </div>

            <div className="text-center mt-8">
              <button
                onClick={restart}
                className="btn-glow text-white px-6 py-2.5 rounded-xl text-sm font-medium"
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
