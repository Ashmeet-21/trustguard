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
        // Backend caps these at 2000 / 5000 points — send the most recent ones
        onComplete({
          keystrokes: keystrokesRef.current.slice(-2000),
          mouse_movements: mouseRef.current.slice(-5000),
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

  // Mark each character as typed: correct = ink, wrong = red underline, not yet typed = faint
  const renderColoredTarget = () => {
    return targetPhrase.split("").map((char, i) => {
      if (i >= typedText.length) {
        return <span key={i} className="text-ink-faint">{char}</span>;
      }
      const match = typedText[i].toLowerCase() === char.toLowerCase();
      return (
        <span key={i} className={match ? "text-ink" : "text-fail underline decoration-2"}>
          {char}
        </span>
      );
    });
  };

  return (
    <div ref={containerRef} onMouseMove={handleMouseMove} className="space-y-5">
      <blockquote className="border-l-[3px] border-seal bg-seal-tint/50 px-5 py-4 rounded-r-[4px]">
        <p className="text-xl leading-snug font-medium" aria-label={targetPhrase}>
          {typedText.length > 0 ? renderColoredTarget() : <span className="text-ink">{targetPhrase}</span>}
        </p>
      </blockquote>

      {completed ? (
        <div className="flex flex-wrap items-center gap-3">
          <p className="note note-pass flex-1 min-w-[14rem]">
            <span>
              Done: {keystrokesRef.current.length} keystrokes and {mouseRef.current.length} mouse points
              recorded, {accuracy}% accurate.
            </span>
          </p>
          <button onClick={resetTracker} className="btn btn-quiet">Type it again</button>
        </div>
      ) : (
        <div>
          <label htmlFor="typing-test" className="block text-sm font-medium text-ink mb-1.5">
            Type the sentence above
          </label>
          <input
            id="typing-test"
            type="text"
            value={typedText}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            autoComplete="off"
            spellCheck={false}
            className="field text-lg"
            autoFocus
          />
          <div className="mt-2 flex flex-wrap justify-between gap-2 text-sm text-ink-faint figures">
            <span>
              {typedText.length} of {targetPhrase.length} characters
              {typedText.length > 0 && (
                <span className={accuracy >= MIN_ACCURACY ? "text-pass" : "text-review"}>, {accuracy}% match</span>
              )}
            </span>
            <span>Move your mouse as you normally would.</span>
          </div>
          <div className="mt-2 h-1 bg-rule rounded-full overflow-hidden" aria-hidden="true">
            <div
              className="h-full bg-seal transition-[width] duration-200"
              style={{ width: `${Math.min(100, (typedText.length / targetPhrase.length) * 100)}%` }}
            />
          </div>

          {mismatchError && (
            <div className="mt-4 flex flex-wrap items-center gap-3" role="alert">
              <p className="note note-fail flex-1 min-w-[14rem]">
                <span>That doesn’t match the sentence closely enough ({accuracy}%, needs {MIN_ACCURACY}%).</span>
              </p>
              <button onClick={resetTracker} className="btn btn-quiet">Clear and start again</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
