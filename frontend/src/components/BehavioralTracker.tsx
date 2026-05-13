"use client";

import { useRef, useState, useCallback, useEffect } from "react";

interface Props {
  onComplete: (data: BehaviorData) => void;
  onReset?: () => void;
}

export interface BehaviorData {
  keystrokes: { key: string; timestamp_ms: number }[];
  mouse_movements: { x: number; y: number; timestamp_ms: number }[];
}

const TARGET_PHRASES = [
  "Trust is built through verification",
  "Every identity deserves protection today",
  "Security starts with the first step",
  "Verify once and access anywhere safely",
  "Digital trust powers modern security now",
  "Strong passwords protect your digital life",
  "Privacy and safety go hand in hand",
  "Authentic identity is worth protecting well",
];

function pickRandom(exclude?: number): number {
  let idx: number;
  do {
    idx = Math.floor(Math.random() * TARGET_PHRASES.length);
  } while (idx === exclude && TARGET_PHRASES.length > 1);
  return idx;
}

/** Calculate how accurately the typed text matches the target (0-100%) */
function calcAccuracy(typed: string, target: string): number {
  if (typed.length === 0) return 0;
  const len = Math.min(typed.length, target.length);
  let matches = 0;
  for (let i = 0; i < len; i++) {
    if (typed[i].toLowerCase() === target[i].toLowerCase()) matches++;
  }
  return Math.round((matches / target.length) * 100);
}

const MIN_ACCURACY = 80;

export default function BehavioralTracker({ onComplete, onReset }: Props) {
  const [phraseIndex, setPhraseIndex] = useState(() => pickRandom());
  const [typedText, setTypedText] = useState("");
  const [completed, setCompleted] = useState(false);
  const [accuracy, setAccuracy] = useState(0);
  const [mismatchError, setMismatchError] = useState(false);
  const keystrokesRef = useRef<{ key: string; timestamp_ms: number }[]>([]);
  const mouseRef = useRef<{ x: number; y: number; timestamp_ms: number }[]>([]);
  const startTimeRef = useRef(Date.now());
  const containerRef = useRef<HTMLDivElement>(null);

  const targetPhrase = TARGET_PHRASES[phraseIndex];

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    keystrokesRef.current.push({
      key: e.key,
      timestamp_ms: Date.now() - startTimeRef.current,
    });
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const last = mouseRef.current[mouseRef.current.length - 1];
    const now = Date.now() - startTimeRef.current;
    if (last && now - last.timestamp_ms < 50) return;

    mouseRef.current.push({
      x: e.clientX,
      y: e.clientY,
      timestamp_ms: now,
    });
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setTypedText(val);
    setMismatchError(false);

    const acc = calcAccuracy(val, targetPhrase);
    setAccuracy(acc);

    // Check completion: must reach target length AND accuracy >= threshold
    if (val.length >= targetPhrase.length) {
      if (acc >= MIN_ACCURACY) {
        setCompleted(true);
        onComplete({
          keystrokes: keystrokesRef.current,
          mouse_movements: mouseRef.current,
        });
      } else {
        setMismatchError(true);
      }
    }
  };

  const resetTracker = useCallback(() => {
    setTypedText("");
    setCompleted(false);
    setAccuracy(0);
    setMismatchError(false);
    keystrokesRef.current = [];
    mouseRef.current = [];
    startTimeRef.current = Date.now();
    // Pick a NEW random phrase each time
    setPhraseIndex((prev) => pickRandom(prev));
    onReset?.();
  }, [onReset]);

  useEffect(() => {
    startTimeRef.current = Date.now();
  }, []);

  // Color-code each character: green=correct, red=wrong
  const renderColoredTarget = () => {
    return targetPhrase.split("").map((char, i) => {
      if (i >= typedText.length) {
        return <span key={i} className="text-[#555]">{char}</span>;
      }
      const match = typedText[i].toLowerCase() === char.toLowerCase();
      return (
        <span key={i} className={match ? "text-[#4ade80]" : "text-[#f87171] underline"}>
          {char}
        </span>
      );
    });
  };

  return (
    <div ref={containerRef} onMouseMove={handleMouseMove} className="space-y-4">
      <div className="bg-[#0d0520] border border-[#2d1b69] rounded-xl p-4 text-center">
        <p className="text-xs text-[#999] mb-2 uppercase tracking-wider">Type this sentence exactly</p>
        <p className="text-lg font-medium font-mono tracking-wide">
          {typedText.length > 0 ? renderColoredTarget() : (
            <span className="text-white">&ldquo;{targetPhrase}&rdquo;</span>
          )}
        </p>
      </div>

      {completed ? (
        <div className="bg-[#0d2e1a] border border-[#166534] rounded-xl p-4 text-center">
          <div className="text-2xl mb-2">&#9989;</div>
          <p className="text-[#4ade80] font-medium">Behavioral data captured</p>
          <p className="text-xs text-[#666] mt-1">
            {keystrokesRef.current.length} keystrokes, {mouseRef.current.length} mouse points — {accuracy}% accuracy
          </p>
          <button
            onClick={resetTracker}
            className="text-xs text-[#666] hover:text-white mt-2 underline"
          >
            Try again
          </button>
        </div>
      ) : (
        <div>
          {mismatchError && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-3 mb-3 text-xs">
              Text doesn&apos;t match the phrase above ({accuracy}% accuracy, need {MIN_ACCURACY}%). Please clear and try again.
            </div>
          )}

          <input
            type="text"
            value={typedText}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Start typing the exact phrase here..."
            className="w-full px-4 py-3 bg-[#111] border border-[#333] rounded-xl text-white placeholder-[#555] focus:outline-none focus:border-[#7b2ff7] transition text-sm"
            autoFocus
          />
          <div className="flex justify-between mt-2">
            <span className="text-xs text-[#666]">
              {typedText.length}/{targetPhrase.length} characters
              {typedText.length > 0 && (
                <span className={accuracy >= MIN_ACCURACY ? " text-[#4ade80]" : accuracy >= 50 ? " text-[#fbbf24]" : " text-[#f87171]"}>
                  {" "}({accuracy}% match)
                </span>
              )}
            </span>
            <span className="text-xs text-[#666]">
              Move your mouse around while typing
            </span>
          </div>
          <div className="w-full h-1.5 bg-[#1a1a1a] rounded-full mt-2 overflow-hidden">
            <div
              className="h-full rounded-full gradient-bg transition-all duration-300"
              style={{ width: `${Math.min(100, (typedText.length / targetPhrase.length) * 100)}%` }}
            />
          </div>

          {mismatchError && (
            <button
              onClick={resetTracker}
              className="mt-3 text-sm text-[#999] hover:text-white border border-[#333] px-4 py-2 rounded-lg transition"
            >
              Clear & Start Over
            </button>
          )}
        </div>
      )}
    </div>
  );
}
