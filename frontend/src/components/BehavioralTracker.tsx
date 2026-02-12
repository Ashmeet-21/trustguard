"use client";

import { useRef, useState, useCallback, useEffect } from "react";

interface Props {
  onComplete: (data: BehaviorData) => void;
}

export interface BehaviorData {
  keystrokes: { key: string; timestamp_ms: number }[];
  mouse_movements: { x: number; y: number; timestamp_ms: number }[];
}

export default function BehavioralTracker({ onComplete }: Props) {
  const [typedText, setTypedText] = useState("");
  const [completed, setCompleted] = useState(false);
  const keystrokesRef = useRef<{ key: string; timestamp_ms: number }[]>([]);
  const mouseRef = useRef<{ x: number; y: number; timestamp_ms: number }[]>([]);
  const startTimeRef = useRef(Date.now());
  const containerRef = useRef<HTMLDivElement>(null);

  const targetPhrase = "Trust is built through verification";

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    keystrokesRef.current.push({
      key: e.key,
      timestamp_ms: Date.now() - startTimeRef.current,
    });
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    // Sample every 50ms to avoid too much data
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

    if (val.length >= targetPhrase.length) {
      setCompleted(true);
      onComplete({
        keystrokes: keystrokesRef.current,
        mouse_movements: mouseRef.current,
      });
    }
  };

  useEffect(() => {
    startTimeRef.current = Date.now();
  }, []);

  return (
    <div ref={containerRef} onMouseMove={handleMouseMove} className="space-y-4">
      <div className="bg-[#0d0520] border border-[#2d1b69] rounded-xl p-4 text-center">
        <p className="text-xs text-[#999] mb-2 uppercase tracking-wider">Type this sentence</p>
        <p className="text-lg text-white font-medium">&ldquo;{targetPhrase}&rdquo;</p>
      </div>

      {completed ? (
        <div className="bg-[#0d2e1a] border border-[#166534] rounded-xl p-4 text-center">
          <div className="text-2xl mb-2">&#9989;</div>
          <p className="text-[#4ade80] font-medium">Behavioral data captured</p>
          <p className="text-xs text-[#666] mt-1">
            {keystrokesRef.current.length} keystrokes, {mouseRef.current.length} mouse points
          </p>
        </div>
      ) : (
        <div>
          <input
            type="text"
            value={typedText}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Start typing here..."
            className="w-full px-4 py-3 bg-[#111] border border-[#333] rounded-xl text-white placeholder-[#555] focus:outline-none focus:border-[#7b2ff7] transition text-sm"
            autoFocus
          />
          <div className="flex justify-between mt-2">
            <span className="text-xs text-[#666]">
              {typedText.length}/{targetPhrase.length} characters
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
        </div>
      )}
    </div>
  );
}
