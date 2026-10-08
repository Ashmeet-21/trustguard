"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import StepWizard from "@/components/StepWizard";
import CameraCapture from "@/components/CameraCapture";
import AudioRecorder from "@/components/AudioRecorder";
import BehavioralTracker from "@/components/BehavioralTracker";
import VerificationDocument from "@/components/VerificationDocument";
import { createSession, runVerification, checkFace, type SessionResult } from "@/lib/api";
import type { BehaviorData } from "@/components/BehavioralTracker";

/** Plain-English quality gate results */
function gateInfo(gate: string, passed: boolean): { title: string; description: string } {
  switch (gate) {
    case "replay_protection":
      return passed
        ? { title: "New photo", description: "This photo hasn’t been used in any earlier verification." }
        : { title: "Photo used before", description: "This exact photo was already submitted in another session, so it may be a replay. Take a new selfie." };
    case "minimum_signals":
      return passed
        ? { title: "Enough checks ran", description: "At least two checks completed, so the decision doesn’t rest on one signal." }
        : { title: "Too few checks ran", description: "Only one check completed. At least two are needed for an automatic pass." };
    case "signal_agreement":
      return passed
        ? { title: "Checks agree", description: "The checks reached similar conclusions." }
        : { title: "Checks disagree", description: "One check looked safe while another looked risky. That mismatch needs a person to review." };
    default:
      return { title: gate.replace(/_/g, " "), description: passed ? "Passed." : "Failed." };
  }
}

const AGENT_LABELS: Record<string, string> = {
  image_agent: "face check",
  video_agent: "liveness check",
  voice_agent: "voice check",
  behavior_agent: "typing check",
};

/** Explanation lines not already shown elsewhere (check scores are on the record, gates have their own list). */
function extraNotes(lines: string[]): string[] {
  return lines
    .filter((l) => !/^\w+_agent: (PASSED|FLAGGED)/.test(l) && !/^Quality gate/.test(l))
    .map((l) => l.replace(/\b(image|video|voice|behavior)_agent\b/g, (m) => AGENT_LABELS[m] || m));
}

const STEPS = [
  { label: "Photo", detail: "A selfie of your face" },
  { label: "Voice", detail: "Read one sentence aloud" },
  { label: "Typing", detail: "Type one sentence" },
  { label: "Result", detail: "Your verification record" },
];

export default function VerifyPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  const [currentStep, setCurrentStep] = useState(0);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [behaviorData, setBehaviorData] = useState<BehaviorData | null>(null);
  const [result, setResult] = useState<SessionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  // Face validation state
  const [faceChecking, setFaceChecking] = useState(false);
  const [faceValid, setFaceValid] = useState(false);
  const [faceError, setFaceError] = useState<string | null>(null);

  // Preview URL for the selfie (shown on the verification record)
  useEffect(() => {
    if (!imageFile) {
      setPhotoUrl(null);
      return;
    }
    const url = URL.createObjectURL(imageFile);
    setPhotoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [imageFile]);

  if (authLoading || !user) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-24 flex items-center gap-3 text-ink-soft">
        <div className="spinner w-5 h-5" />
        Loading…
      </div>
    );
  }

  const handleImageCapture = async (file: File) => {
    setImageFile(file);
    setFaceError(null);
    setFaceValid(false);
    setFaceChecking(true);

    try {
      const check = await checkFace(file);
      if (!check.faceDetected) {
        setFaceError("No face found. Take a clear selfie with your whole face inside the oval.");
        setImageFile(null);
      } else if (check.faceBbox) {
        const bbox = check.faceBbox;
        const EDGE = 0.04;
        const cutSides: string[] = [];
        if (bbox.x_min < EDGE) cutSides.push("left");
        if (bbox.y_min < EDGE) cutSides.push("top");
        if (bbox.x_max > 1 - EDGE) cutSides.push("right");
        if (bbox.y_max > 1 - EDGE) cutSides.push("bottom");

        if (cutSides.length > 0) {
          setFaceError(`Your face is cut off at the ${cutSides.join(" and ")}. Centre your whole face inside the oval.`);
          setImageFile(null);
        } else if (bbox.width_pct < 0.15 || bbox.height_pct < 0.18) {
          setFaceError("Your face is too small in the photo. Move closer so it fills the oval.");
          setImageFile(null);
        } else if (check.livenessScore < 0.3) {
          setFaceError("The photo looks blurry or taken from a screen. Take a sharp, well-lit selfie directly with your camera.");
          setImageFile(null);
        } else if (check.livenessScore < 0.5) {
          setFaceError("The photo is unclear. Find better light and hold the camera steady.");
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

  const handleImageReset = () => {
    setImageFile(null);
    setFaceValid(false);
    setFaceError(null);
  };

  const nextStep = () => setCurrentStep((s) => s + 1);
  const prevStep = () => setCurrentStep((s) => Math.max(0, s - 1));

  const runFullVerification = async () => {
    setCurrentStep(3);
    setProcessing(true);
    setError(null);
    try {
      const session = await createSession();
      const res = await runVerification(session.session_id, imageFile || undefined, audioBlob || undefined, behaviorData || undefined);
      setResult(res);
      setCurrentStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The verification could not be completed.");
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

  const stepHeading = (title: string, body: string) => (
    <div className="mb-6">
      <h2 className="text-xl font-bold text-ink">{title}</h2>
      <p className="mt-1 text-ink-soft max-w-[60ch]">{body}</p>
    </div>
  );

  const navButtons = (onNext: () => void, nextLabel: string, nextDisabled: boolean, showBack = true) => (
    <div className="flex items-center justify-between gap-3 mt-8 pt-6 border-t border-rule">
      {showBack ? (
        <button onClick={prevStep} className="btn btn-quiet">Back</button>
      ) : <span />}
      <button onClick={onNext} disabled={nextDisabled} className="btn">{nextLabel}</button>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto px-6 py-10 md:py-14">
      <h1 className="text-[2rem] md:text-[2.5rem] font-bold leading-tight tracking-[-0.02em] text-ink">
        Verify your identity
      </h1>
      <p className="mt-2 text-ink-soft">Three short steps. Your camera and microphone are only used while a step is open.</p>

      <div className="mt-10 grid md:grid-cols-[14rem_1fr] gap-8 md:gap-12 items-start">
        <StepWizard steps={STEPS} currentStep={Math.min(currentStep, 3)} />

        <div>
          {error && (
            <p className="note note-fail mb-6" role="alert">
              <span><strong className="font-semibold">The checks didn’t finish.</strong> {error}</span>
            </p>
          )}

          {currentStep === 0 && (
            <section className="sheet p-6 sm:p-8">
              {stepHeading("Take a selfie", "Use your camera or upload a photo. It’s checked for signs of AI generation and for a live person.")}
              <CameraCapture onCapture={handleImageCapture} onReset={handleImageReset} />

              <div className="mt-4" aria-live="polite">
                {faceChecking && (
                  <p className="flex items-center gap-2.5 text-ink-soft">
                    <span className="spinner w-4 h-4" /> Checking the photo for a face…
                  </p>
                )}
                {faceValid && !faceChecking && (
                  <p className="note note-pass"><span>Face found. You can continue.</span></p>
                )}
                {faceError && <p className="note note-fail"><span>{faceError}</span></p>}
              </div>

              {navButtons(nextStep, "Continue to voice", !imageFile || !faceValid || faceChecking, false)}
            </section>
          )}

          {currentStep === 1 && (
            <section className="sheet p-6 sm:p-8">
              {stepHeading("Read a sentence aloud", "Record yourself reading the sentence below. The recording is checked for signs of a synthetic voice.")}
              <AudioRecorder onRecording={setAudioBlob} onReset={() => setAudioBlob(null)} />
              {navButtons(nextStep, "Continue to typing", !audioBlob)}
            </section>
          )}

          {currentStep === 2 && (
            <section className="sheet p-6 sm:p-8">
              {stepHeading("Type a sentence", "Type the sentence below and move your mouse as you normally would. The timing is checked for scripted input.")}
              <BehavioralTracker onComplete={setBehaviorData} onReset={() => setBehaviorData(null)} />
              {navButtons(runFullVerification, "Run the checks", !behaviorData)}
            </section>
          )}

          {currentStep === 3 && processing && (
            <section className="sheet p-6 sm:p-8" aria-live="polite" aria-busy="true">
              {stepHeading("Running the checks", "This usually takes 5–10 seconds. If the server has been idle, it can take up to a minute to start.")}
              <ul className="divide-y divide-rule border-y border-rule">
                {[
                  imageFile && "Face is not AI-generated",
                  imageFile && "A live person, not a photo of one",
                  audioBlob && "Voice is human, not synthetic",
                  behaviorData && "Typing is human, not scripted",
                ].filter(Boolean).map((label) => (
                  <li key={label as string} className="py-3 flex items-center gap-3 text-ink">
                    <span className="spinner w-4 h-4 shrink-0" /> {label}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {currentStep === 4 && result && (
            <section>
              <VerificationDocument
                animate
                decision={result.decision}
                trustScore={result.trust_score}
                photoUrl={photoUrl}
                holder={user.full_name || user.email}
                sessionId={result.session_id}
                checks={Object.entries(result.agents).map(([key, a]) => ({ key, score: a.score, risk: a.risk_level }))}
              />

              <div className="mt-8 grid lg:grid-cols-2 gap-8">
                {result.quality_gates && result.quality_gates.length > 0 && (
                  <div>
                    <h2 className="font-bold text-ink text-lg">Quality gates</h2>
                    <ul className="mt-3 divide-y divide-rule border-y border-rule">
                      {result.quality_gates.map((gate) => {
                        const info = gateInfo(gate.gate, gate.passed);
                        return (
                          <li key={gate.gate} className="py-3 flex gap-3">
                            <span
                              className={`mt-1 shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-white text-[0.625rem] font-bold ${gate.passed ? "bg-pass" : "bg-fail"}`}
                              aria-hidden="true"
                            >
                              {gate.passed ? "✓" : "!"}
                            </span>
                            <span>
                              <span className="block font-medium text-ink">
                                {info.title}<span className="sr-only">{gate.passed ? " (passed)" : " (failed)"}</span>
                              </span>
                              <span className="block text-sm text-ink-soft">{info.description}</span>
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                <div>
                  <h2 className="font-bold text-ink text-lg">Details</h2>
                  <dl className="mt-3 divide-y divide-rule border-y border-rule text-sm">
                    <div className="py-3 flex justify-between gap-4">
                      <dt className="text-ink-soft">Session</dt>
                      <dd className="font-mono text-ink">{result.session_id}</dd>
                    </div>
                    <div className="py-3 flex justify-between gap-4">
                      <dt className="text-ink-soft">Processing time</dt>
                      <dd className="text-ink figures">{(result.processing_time_ms / 1000).toFixed(1)} s</dd>
                    </div>
                  </dl>
                  {extraNotes(result.explanation || []).length > 0 && (
                    <ul className="mt-4 space-y-2">
                      {extraNotes(result.explanation).map((line) => (
                        <li key={line} className="note note-review"><span>{line}</span></li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div className="mt-10 flex flex-wrap gap-3">
                <button onClick={restart} className="btn">Verify again</button>
                <Link href="/dashboard" className="btn btn-quiet">Open dashboard</Link>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
